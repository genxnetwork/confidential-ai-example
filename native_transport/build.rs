// Build-time only. The runtime verifier does not access files or spawn processes.
fn stamp(scope: &str, relative_root: &str) {
    use std::{env, path::Path, process::Command};
    let dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let root = Path::new(&dir).join(relative_root).canonicalize().unwrap();
    let output = Command::new("python3")
        .arg(root.join("scripts/source_fingerprint.py"))
        .arg(&root)
        .arg(scope)
        .output()
        .expect("Python 3 is required to fingerprint build sources");
    assert!(
        output.status.success(),
        "source fingerprint failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let text = String::from_utf8(output.stdout).unwrap();
    let mut lines = text.lines();
    println!(
        "cargo:rustc-env=CONFIDO_SOURCE_SHA256={}",
        lines.next().unwrap()
    );
    for path in lines {
        println!("cargo:rerun-if-changed={path}");
    }
    let rustc = Command::new(env::var("RUSTC").unwrap_or("rustc".into()))
        .arg("--version")
        .output()
        .unwrap();
    println!(
        "cargo:rustc-env=CONFIDO_RUSTC={}",
        String::from_utf8_lossy(&rustc.stdout).trim()
    );
    println!(
        "cargo:rustc-env=CONFIDO_TARGET={}",
        env::var("TARGET").unwrap()
    );
    println!("cargo:rerun-if-env-changed=RUSTFLAGS");
    println!("cargo:rerun-if-env-changed=CARGO_ENCODED_RUSTFLAGS");
    println!(
        "cargo:rustc-env=CONFIDO_BUILD_FLAGS={}",
        env::var("CARGO_ENCODED_RUSTFLAGS")
            .unwrap_or_default()
            .replace('\x1f', " ")
    );
    let mut features: Vec<_> = env::vars()
        .filter_map(|(name, _)| name.strip_prefix("CARGO_FEATURE_").map(str::to_owned))
        .collect();
    features.sort();
    println!(
        "cargo:rustc-env=CONFIDO_BUILD_FEATURES={}",
        features.join(",")
    );
    println!(
        "cargo:rustc-env=CONFIDO_BUILD_PROFILE={}",
        env::var("PROFILE").unwrap()
    );
}

fn main() {
    stamp("transport", "..");
}
