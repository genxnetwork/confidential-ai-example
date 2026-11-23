//! Application-owned transport. Has no evidence verification or admission logic.
use openssl::{asn1::Asn1Time, x509::X509};
use pyo3::{prelude::*, types::PyBytes};
use reqwest::{Client, Url};
use rustls::{
    client::{ServerCertVerified, ServerCertVerifier},
    Certificate, ClientConfig, Error as TlsError, RootCertStore, ServerName,
};
use std::{
    cmp::Ordering,
    error::Error,
    net::IpAddr,
    sync::Arc,
    time::{Duration, SystemTime, UNIX_EPOCH},
};
const MAX_BODY: usize = 4 * 1024 * 1024;
/// Every TLS connection must present the exact certificate bound into the
/// appraised quote. This works for both public-CA and self-signed leaf certs;
/// rustls still verifies the server's TLS handshake signature.
struct AttestedCertificateVerifier {
    expected_der: Vec<u8>,
    expected_host: String,
}

impl ServerCertVerifier for AttestedCertificateVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &Certificate,
        _intermediates: &[Certificate],
        server_name: &ServerName,
        _scts: &mut dyn Iterator<Item = &[u8]>,
        _ocsp_response: &[u8],
        now: SystemTime,
    ) -> Result<ServerCertVerified, TlsError> {
        let fail = || {
            TlsError::General(
                "TLS certificate does not match appraised evidence or hostname".into(),
            )
        };
        if end_entity.0 != self.expected_der {
            return Err(fail());
        }
        let x509 = X509::from_der(&end_entity.0).map_err(|_| fail())?;
        let now_unix = now
            .duration_since(UNIX_EPOCH)
            .map_err(|_| fail())?
            .as_secs();
        let now_asn1 =
            Asn1Time::from_unix(now_unix.try_into().map_err(|_| fail())?).map_err(|_| fail())?;
        if x509.not_before().compare(&now_asn1).map_err(|_| fail())? == Ordering::Greater
            || x509.not_after().compare(&now_asn1).map_err(|_| fail())? == Ordering::Less
        {
            return Err(fail());
        }
        let names = x509.subject_alt_names().ok_or_else(fail)?;
        let host_matches = match server_name {
            ServerName::DnsName(host)
                if host.as_ref().eq_ignore_ascii_case(&self.expected_host) =>
            {
                names.iter().any(|name| {
                    name.dnsname()
                        .is_some_and(|dns| dns.eq_ignore_ascii_case(host.as_ref()))
                })
            }
            ServerName::IpAddress(ip) if ip.to_string() == self.expected_host => {
                names.iter().any(|name| {
                    name.ipaddress().is_some_and(|addr| match ip {
                        IpAddr::V4(v4) => addr == v4.octets(),
                        IpAddr::V6(v6) => addr == v6.octets(),
                    })
                })
            }
            _ => false,
        };
        if !host_matches {
            return Err(fail());
        }
        Ok(ServerCertVerified::assertion())
    }
}

fn appraised_tls_config(der: Vec<u8>, hostname: String) -> ClientConfig {
    let mut config = ClientConfig::builder()
        .with_safe_defaults()
        .with_root_certificates(RootCertStore::empty())
        .with_no_client_auth();
    // Require the certificate verifier on every new connection, including after rotation.
    config.resumption = rustls::client::Resumption::disabled();
    config
        .dangerous()
        .set_certificate_verifier(Arc::new(AttestedCertificateVerifier {
            expected_der: der,
            expected_host: hostname,
        }));
    config
}

pub fn origin_url(s: &str) -> Result<Url, String> {
    let u = Url::parse(s).map_err(|e| e.to_string())?;
    if u.scheme() != "https"
        || u.host_str().is_none()
        || !u.username().is_empty()
        || u.password().is_some()
        || u.path() != "/"
        || u.query().is_some()
        || u.fragment().is_some()
    {
        return Err(
            "Expected a bare HTTPS origin without credentials, path, query or fragment".into(),
        );
    }
    Ok(u)
}

pub struct AppraisedClient {
    client: Client,
    origin: Url,
}
impl AppraisedClient {
    pub async fn request(
        &self,
        method: &str,
        url: &str,
        headers: &[(String, String)],
        body: Vec<u8>,
    ) -> Result<(u16, Vec<(String, String)>, Vec<u8>), Box<dyn Error>> {
        let target = Url::parse(url)?;
        if target.origin() != self.origin.origin()
            || target.scheme() != "https"
            || !target.username().is_empty()
            || target.password().is_some()
            || target.fragment().is_some()
        {
            return Err("Application request is outside the appraised HTTPS origin".into());
        }
        let mut request = self.client.request(method.parse()?, target).body(body);
        for (k, v) in headers {
            if [
                "host",
                "connection",
                "transfer-encoding",
                "content-length",
                "proxy-authorization",
            ]
            .contains(&k.to_ascii_lowercase().as_str())
            {
                // reqwest computes authority/framing; caller cannot redirect it.
                continue;
            }
            request = request.header(k, v);
        }
        let mut response = request.send().await?;
        if response.status().is_redirection() {
            return Err("Application redirects are disabled".into());
        }
        let status = response.status().as_u16();
        let headers = response
            .headers()
            .iter()
            .filter_map(|(k, v)| v.to_str().ok().map(|v| (k.to_string(), v.to_string())))
            .collect();
        let mut bytes = vec![];
        while let Some(chunk) = response.chunk().await? {
            if bytes.len() + chunk.len() > MAX_BODY {
                return Err("Application response exceeds size limit".into());
            }
            bytes.extend_from_slice(&chunk);
        }
        Ok((status, headers, bytes))
    }
}

fn error(e: impl ToString) -> PyErr {
    pyo3::exceptions::PyRuntimeError::new_err(e.to_string())
}

type PythonResponse = (u16, Vec<(String, String)>, Py<PyBytes>);

#[pyclass]
struct Session {
    runtime: tokio::runtime::Runtime,
    client: AppraisedClient,
}
// PyO3 0.20 expands this attribute into non-local impls with newer rustc.
#[pymethods]
impl Session {
    #[new]
    fn new(origin: &str, certificate_der: &[u8]) -> PyResult<Self> {
        let origin = origin_url(origin).map_err(error)?;
        X509::from_der(certificate_der).map_err(error)?;
        let tls = appraised_tls_config(
            certificate_der.to_vec(),
            origin
                .host_str()
                .ok_or_else(|| error("Missing host"))?
                .into(),
        );
        let runtime = tokio::runtime::Runtime::new().map_err(error)?;
        let client = runtime
            .block_on(async {
                Client::builder()
                    .use_preconfigured_tls(tls)
                    .https_only(true)
                    .redirect(reqwest::redirect::Policy::none())
                    .timeout(Duration::from_secs(30))
                    .connect_timeout(Duration::from_secs(10))
                    .build()
            })
            .map_err(error)?;
        Ok(Self {
            runtime,
            client: AppraisedClient { client, origin },
        })
    }
    fn request(
        &self,
        py: Python<'_>,
        method: &str,
        url: &str,
        headers: Vec<(String, String)>,
        body: &[u8],
    ) -> PyResult<PythonResponse> {
        let (status, headers, bytes) = py
            .allow_threads(|| {
                self.runtime
                    .block_on(self.client.request(method, url, &headers, body.to_vec()))
                    .map_err(|e| e.to_string())
            })
            .map_err(error)?;
        Ok((status, headers, PyBytes::new(py, &bytes).into()))
    }
}
#[pyfunction]
fn build_info() -> std::collections::HashMap<String, String> {
    [
        ("version", env!("CARGO_PKG_VERSION")),
        ("source_sha256", env!("CONFIDO_SOURCE_SHA256")),
        ("target", env!("CONFIDO_TARGET")),
        ("rustc", env!("CONFIDO_RUSTC")),
        ("flags", env!("CONFIDO_BUILD_FLAGS")),
        ("features", env!("CONFIDO_BUILD_FEATURES")),
        ("build_profile", env!("CONFIDO_BUILD_PROFILE")),
    ]
    .into_iter()
    .map(|(k, v)| (k.into(), v.into()))
    .collect()
}
#[pymodule]
fn _confai_transport(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    m.add_function(wrap_pyfunction!(build_info, m)?)?;
    m.add_class::<Session>()?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pinned_tls_leaf_requires_exact_certificate_host_and_validity() {
        use openssl::{
            hash::MessageDigest,
            pkey::PKey,
            rsa::Rsa,
            x509::{extension::SubjectAlternativeName, X509NameBuilder},
        };
        let key = PKey::from_rsa(Rsa::generate(2048).unwrap()).unwrap();
        let mut name = X509NameBuilder::new().unwrap();
        name.append_entry_by_text("CN", "match.demo.genxt.network")
            .unwrap();
        let name = name.build();
        let mut builder = X509::builder().unwrap();
        builder.set_version(2).unwrap();
        builder.set_subject_name(&name).unwrap();
        builder.set_issuer_name(&name).unwrap();
        builder.set_pubkey(&key).unwrap();
        builder
            .set_not_before(&Asn1Time::days_from_now(0).unwrap())
            .unwrap();
        builder
            .set_not_after(&Asn1Time::days_from_now(1).unwrap())
            .unwrap();
        let san = SubjectAlternativeName::new()
            .dns("match.demo.genxt.network")
            .build(&builder.x509v3_context(None, None))
            .unwrap();
        builder.append_extension(san).unwrap();
        builder.sign(&key, MessageDigest::sha256()).unwrap();
        let der = builder.build().to_der().unwrap();
        let verifier = AttestedCertificateVerifier {
            expected_der: der.clone(),
            expected_host: "match.demo.genxt.network".into(),
        };
        let name = ServerName::try_from("match.demo.genxt.network").unwrap();
        let mut scts = std::iter::empty();
        assert!(verifier
            .verify_server_cert(
                &Certificate(der.clone()),
                &[],
                &name,
                &mut scts,
                &[],
                SystemTime::now()
            )
            .is_ok());
        assert!(verifier
            .verify_server_cert(
                &Certificate(vec![1, 2, 3]),
                &[],
                &name,
                &mut scts,
                &[],
                SystemTime::now()
            )
            .is_err());
        let wrong_name = ServerName::try_from("mismatch.demo.genxt.network").unwrap();
        assert!(verifier
            .verify_server_cert(
                &Certificate(der.clone()),
                &[],
                &wrong_name,
                &mut scts,
                &[],
                SystemTime::now()
            )
            .is_err());
        assert!(verifier
            .verify_server_cert(
                &Certificate(der),
                &[],
                &name,
                &mut scts,
                &[],
                SystemTime::now() + Duration::from_secs(2 * 86400)
            )
            .is_err());
    }
    #[tokio::test]
    async fn scoped_client_rejects_other_origin_before_network() {
        let client = AppraisedClient {
            client: Client::new(),
            origin: origin_url("https://localhost:19443").unwrap(),
        };
        for target in [
            "https://localhost:19444/v1",
            "https://127.0.0.1:19443/v1",
            "http://localhost:19443/v1",
            "https://u:p@localhost:19443/v1",
        ] {
            assert!(client
                .request(
                    "POST",
                    target,
                    &[("authorization".into(), "must-not-leave".into())],
                    vec![]
                )
                .await
                .unwrap_err()
                .to_string()
                .contains("outside"));
        }
    }
}
