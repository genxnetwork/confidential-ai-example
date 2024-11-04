```bash
pavelmacbook:~/confidential-ai-example$ sudo make chat
docker run --platform linux/amd64 -it confidential-ai-example python3 confai-promter.py
[2024-11-04T17:10:20Z INFO  confido::atls] fn aTLS_connect: "http://api.genxt.ai:9000"
[2024-11-04T17:10:20Z DEBUG confido::atls] host: "http://api.genxt.ai:9000"
[2024-11-04T17:10:20Z INFO  confido::atls] Connecting to http://api.genxt.ai:9000 to gather evidence, nonce: "rXG7TpMH4jofHVoxxfu80sowW54YCTgH62vaT479ymE="
[2024-11-04T17:10:20Z DEBUG reqwest::connect] starting new connection: http://api.genxt.ai:9000/
[2024-11-04T17:10:21Z DEBUG confido::atls] aTLS response: Evidence {
        report: "48434c410200000084090000020000000000000000000000000000000000000002000000070001001f0003000000000001000000000000000000000000000000020000000000000000000000000000000000000001000000080000000000154800000000000000000000000000000000b1642acef5e2f8a6293809d8b505895c1ebccc2014c6cd3aecca104788ea2f02000000000000000000000000000000000000000000000000000000000000000074acaf35e63d387cb49619e3857afde520f54c43f82985e0ee0986173908a78b52f9c2c896558ed78b14735832bd88bd00000000000000000000000000000000000000000000000000000000000000000356215882a825279a85b300b0b742931d113bf7e32dde2e50ffde7ec743ca491ecdd7f336dc28a6e0b2bb57af7a44a30000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006a604aaf95ac025cf9d3b7c864e3751562aef436329ea72d860c40b64608b053ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff08000000000010440000000000000000000000000000000000000000000000002ba5395d906e01b34155c4dcfa440a744ec18afde6948810230fc05e20521d58935d3895ca2a52d87159daa06a178fdbbbb67eb8150627cfe4cd80e05df2e8850800000000001048243701001c3701000800000000001044000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000a145ad9183c0fb812ca74a9aa711759adaff44c5da8ce0e94baa2974d0d81cdfe4922768e080efe6cdb79a41a0c25f32000000000000000000000000000000000000000000000000e1561f8255eee827dfb87eeae0b4b4609474f0a3c021cfd18595b2eb7eea0e2aa7dfb0a9512d1884937e143af46a05200000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c4040000010000000200000001000000b00400007b226b657973223a5b7b226b6964223a2248434c416b507562222c226b65795f6f7073223a5b227369676e225d2c226b7479223a22525341222c2265223a2241514142222c226e223a22334950464c414142516b2d4d5f42774d34452d416c38544b6a2d47756c6830473167504733644b335858746c63704f5f35454b713852715f68692d3643374c5343515262302d444861517a635276437574632d49786f794c4947573475473730764333526357767a4a4f77425979536d476c4c554556625f37743361434a70556771476a6f544c794d5830774f5347584d326833574843307a7677696d576c4f576d70386853304930624f636652775a504d645a4e6e4639624865634d6a54646d6e4e757070786d437743536276624d52374f5746736371714552554f503565724e41507957343970575359712d384e5874684f6c5442754b586b5a6b36797a6274556771714c656b47524a735a48523245455266474f55334a3264334c4d416c584a36396175534a6d6d4a4848574f36303579755848737075685a644962585545635f774b4e6d4f653847355f3035743741444377227d2c7b226b6964223a2248434c456b507562222c226b65795f6f7073223a5b22656e6372797074225d2c226b7479223a22525341222c2265223a2241514142222c226e223a226a50307446774141506778543072394e656d74737838724a4c517330633870705f416f504c326176766230715a795761774f326d364149546c6e656c4e6e55437176736566314e4137654a5a61546543306876496849544e6743776938343246435f3162514f697049524f67466231593475637470696c526f7964647665426c49376241534f4f6933382d626b5843626855416834754a79674b76624434566359324b6f74564d543552484e5462646165374d6e6579747a484767306435484c2d2d393438427733697a526a712d636e574851764a7037694e5266466c7045375767683651774f3938655758696a4f5a44544f6b7a50444932456a6d667965795f36444f2d4637445f3667674d34327357686f44597a3656474456545648584967542d323334744263312d4b4b4e694145363267395f667479315a37796a6a3232314975326d30725855787974344d486468396a3951227d5d2c22766d2d636f6e66696775726174696f6e223a7b22636f6e736f6c652d656e61626c6564223a747275652c22726f6f742d636572742d7468756d627072696e74223a22366e5a5a6e59614a63344b71555a5f7976412d6d75634664594e6f75766c506e49546e4e4d5873486c2d30222c227365637572652d626f6f74223a747275652c2274706d2d656e61626c6564223a747275652c2274706d2d706572736973746564223a747275652c22766d556e697175654964223a2243353144353444442d463033432d344632432d414245332d314638444142323145383336227d2c22757365722d64617461223a223030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030303030227d0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        quote: Quote {
            signature: "b9d978bfc5c8d1f5ed7d6cd78c8203547b3ddba28fe3cb8ec8c2d45e423a5791669b4aa8d47aa1f3000a8243f22c28cb63bf444dec4ea1bb95262d704e3b00035f381de4d1ca45b370ac5abab42e06b907de9abb5f384cbd272963c18b08f13ef699dd80437e94c52b1d275b5b996f3d0cf9508d7c51ee09aeaf42af58cd5152f13c2ec461e9407e2276e064c1e7bd866c00504a9da199085ad08314e6f7f22a4496b9a732c46ac0918cc67b7f3ffcaa9a03eed3bfb0bbd0ef913551eac8cd0b5b29f025fd0c314da1cf14fc0636e161fa467a89c0c835cee05a71e6e3313eaf05e0ab78fcb23c5a354648331b0e4f2af43f164c7349eab4d44725fde425347e",
            message: "ff54434780180022000b9df5c02ede8ad3dcbeeb47fbc09b9d64d36c9dc0e3f6c6235e5f8a91ac4d82ec0020ad71bb4e9307e23a1f1d5a31c5fbbcd2ca305b9e18093807eb6bda4f8efdca61000000054fe80c7c000000100000000001202003120012000300000001000403ffffff00209f333df053189d7c91e66dc00982573a6349879509f4383c570347fddd45b7a1",
            pcr_banks: [
                {
                    algo: Sha1,
                    pcr_values: [
                        "733a683619d3dd46dbf8d78a268076b2fbececd8",
                        "f124a1e2bd2229a347c90475db881922da6fd719",
                        "b2a83b0ebf2f8374299a5b2bdfc31ea955ad7236",
                        "b2a83b0ebf2f8374299a5b2bdfc31ea955ad7236",
                        "ae7939e21358bf8cd0ac5b24397a9265c48d9f56",
                        "e38330d740b4640ad84c34d50ad1bffea7bf20c0",
                        "6436981b752f8e08a10c0f2ae6b5cbe65e04da91",
                        "5028147c7baa7967821bd1868cd057706da8e304",
                        "0000000000000000000000000000000000000000",
                        "70d88a5df6072098e0421bf9dcd02a83eab28e7a",
                        "71185871a0e3f31dc55c729c7426cb922f57fd39",
                        "0000000000000000000000000000000000000000",
                        "2a6d6d4124b1ec83a4d5a69111fb23711e36170f",
                        "0000000000000000000000000000000000000000",
                        "157e07e56e25148f3e4d306a73f82664ec2f80db",
                        "0000000000000000000000000000000000000000",
                        "0000000000000000000000000000000000000000",
                        "ffffffffffffffffffffffffffffffffffffffff",
                        "ffffffffffffffffffffffffffffffffffffffff",
                        "ffffffffffffffffffffffffffffffffffffffff",
                        "ffffffffffffffffffffffffffffffffffffffff",
                        "ffffffffffffffffffffffffffffffffffffffff",
                        "ffffffffffffffffffffffffffffffffffffffff",
                        "0000000000000000000000000000000000000000",
                    ]
                }
                ,
            ],
        },
    }
[2024-11-04T17:10:21Z INFO  confido::atls] aTLS response successfully received
[2024-11-04T17:10:21Z DEBUG ureq::stream] connecting to kdsintf.amd.com:443 at 165.204.91.79:443
[2024-11-04T17:10:21Z DEBUG rustls::client::hs] No cached session for DnsName("kdsintf.amd.com")
[2024-11-04T17:10:21Z DEBUG rustls::client::hs] Not resuming any session
[2024-11-04T17:10:21Z DEBUG rustls::client::hs] ALPN protocol is None
[2024-11-04T17:10:21Z DEBUG rustls::client::hs] Using ciphersuite TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
[2024-11-04T17:10:21Z DEBUG rustls::client::tls12::server_hello] Server supports tickets
[2024-11-04T17:10:21Z DEBUG rustls::client::tls12] ECDHE curve is EcParameters { curve_type: NamedCurve, named_group: X25519 }
[2024-11-04T17:10:21Z DEBUG rustls::client::tls12] Server DNS name is DnsName("kdsintf.amd.com")
[2024-11-04T17:10:21Z DEBUG ureq::stream] created stream: Stream(RustlsStream)
[2024-11-04T17:10:21Z DEBUG ureq::unit] sending request GET https://kdsintf.amd.com/vcek/v1/Genoa/cert_chain
[2024-11-04T17:10:21Z DEBUG ureq::unit] writing prelude: GET /vcek/v1/Genoa/cert_chain HTTP/1.1
    Host: kdsintf.amd.com
    User-Agent: ureq/2.10.1
    Accept: */*
[2024-11-04T17:10:22Z DEBUG ureq::response] Body entirely buffered (length: 4602)
[2024-11-04T17:10:22Z DEBUG ureq::pool] adding stream to pool: https|kdsintf.amd.com|443 -> Stream(RustlsStream)
[2024-11-04T17:10:22Z DEBUG ureq::unit] response 200 to GET https://kdsintf.amd.com/vcek/v1/Genoa/cert_chain
[2024-11-04T17:10:22Z DEBUG ureq::stream] dropping stream: Stream(RustlsStream)
[2024-11-04T17:10:22Z DEBUG ureq::stream] connecting to kdsintf.amd.com:443 at 165.204.91.79:443
[2024-11-04T17:10:22Z DEBUG rustls::client::hs] Resuming session
[2024-11-04T17:10:22Z DEBUG rustls::client::hs] ALPN protocol is None
[2024-11-04T17:10:22Z DEBUG rustls::client::hs] Using ciphersuite TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
[2024-11-04T17:10:22Z DEBUG rustls::client::tls12::server_hello] Server supports tickets
[2024-11-04T17:10:22Z DEBUG rustls::client::tls12::server_hello] Server agreed to resume
[2024-11-04T17:10:22Z DEBUG ureq::stream] created stream: Stream(RustlsStream)
[2024-11-04T17:10:22Z DEBUG ureq::unit] sending request GET https://kdsintf.amd.com/vcek/v1/Genoa/2ba5395d906e01b34155c4dcfa440a744ec18afde6948810230fc05e20521d58935d3895ca2a52d87159daa06a178fdbbbb67eb8150627cfe4cd80e05df2e885?blSPL=08&teeSPL=00&snpSPL=16&ucodeSPL=68
[2024-11-04T17:10:22Z DEBUG ureq::unit] writing prelude: GET /vcek/v1/Genoa/2ba5395d906e01b34155c4dcfa440a744ec18afde6948810230fc05e20521d58935d3895ca2a52d87159daa06a178fdbbbb67eb8150627cfe4cd80e05df2e885?blSPL=08&teeSPL=00&snpSPL=16&ucodeSPL=68 HTTP/1.1
    Host: kdsintf.amd.com
    User-Agent: ureq/2.10.1
    Accept: */*
[2024-11-04T17:10:22Z DEBUG ureq::response] Body entirely buffered (length: 1347)
[2024-11-04T17:10:22Z DEBUG ureq::pool] adding stream to pool: https|kdsintf.amd.com|443 -> Stream(RustlsStream)
[2024-11-04T17:10:22Z DEBUG ureq::unit] response 200 to GET https://kdsintf.amd.com/vcek/v1/Genoa/2ba5395d906e01b34155c4dcfa440a744ec18afde6948810230fc05e20521d58935d3895ca2a52d87159daa06a178fdbbbb67eb8150627cfe4cd80e05df2e885?blSPL=08&teeSPL=00&snpSPL=16&ucodeSPL=68
[2024-11-04T17:10:22Z DEBUG ureq::stream] dropping stream: Stream(RustlsStream)
[2024-11-04T17:10:22Z DEBUG confido::trs] TRS host configured: api.genxt.ai
[2024-11-04T17:10:22Z INFO  confido::trs] Fetching TRS for 172.177.22.106
[2024-11-04T17:10:22Z DEBUG reqwest::connect] starting new connection: https://api.github.com/
[2024-11-04T17:10:22Z DEBUG reqwest::async_impl::client] redirecting 'https://api.github.com/repos/genxnetwork/confido-private/contents/bb-attest-172.177.22.106.json' to 'https://api.github.com/repositories/816818055/contents/bb-attest-172.177.22.106.json'
[2024-11-04T17:10:22Z DEBUG reqwest::connect] starting new connection: https://api.github.com/
[2024-11-04T17:10:22Z INFO  confido::trs] TRS ima-template: ima-ng
[2024-11-04T17:10:22Z DEBUG confido::trs] TRS boot_aggregate template_hash: 45e0217a65881ac2400be3aae6c21f2f83b6372b
[2024-11-04T17:10:22Z DEBUG confido::trs] TRS boot_aggregate filedata_hash: 690106058d5aa385bc44cc09f6a0ad54086298ca
[2024-11-04T17:10:22Z INFO  confido::evidence] calculating boot_aggregate sha1 hash using the vTPM Quote PCR values...
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 0: 733a683619d3dd46dbf8d78a268076b2fbececd8
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 1: f124a1e2bd2229a347c90475db881922da6fd719
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 2: b2a83b0ebf2f8374299a5b2bdfc31ea955ad7236
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 3: b2a83b0ebf2f8374299a5b2bdfc31ea955ad7236
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 4: ae7939e21358bf8cd0ac5b24397a9265c48d9f56
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 5: e38330d740b4640ad84c34d50ad1bffea7bf20c0
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 6: 6436981b752f8e08a10c0f2ae6b5cbe65e04da91
[2024-11-04T17:10:22Z DEBUG confido::evidence] PCR 7: 5028147c7baa7967821bd1868cd057706da8e304
[2024-11-04T17:10:22Z INFO  confido::evidence] calculated boot_aggregate sha1 hash: 690106058d5aa385bc44cc09f6a0ad54086298ca
[2024-11-04T17:10:22Z INFO  confido::evidence] Boot aggregate hash matches
[2024-11-04T17:10:22Z INFO  confido::trs] Calculating PCR10 value from IMA measurements
[2024-11-04T17:10:22Z DEBUG confido::trs] boot_aggregate                                     boot_aggregate                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] autofs4.ko                                         autofs4.ko                                         Match
[2024-11-04T17:10:22Z DEBUG confido::trs] cryptd.ko                                          cryptd.ko                                          Match
[2024-11-04T17:10:22Z DEBUG confido::trs] crypto_simd.ko                                     crypto_simd.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] aesni-intel.ko                                     aesni-intel.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nls_iso8859-1.ko                                   nls_iso8859-1.ko                                   Match
[2024-11-04T17:10:22Z DEBUG confido::trs] dm-crypt.ko                                        dm-crypt.ko                                        Match
[2024-11-04T17:10:22Z DEBUG confido::trs] x_tables.ko                                        x_tables.ko                                        Match
[2024-11-04T17:10:22Z DEBUG confido::trs] ip_tables.ko                                       ip_tables.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] i2c-core.ko                                        i2c-core.ko                                        Match
[2024-11-04T17:10:22Z DEBUG confido::trs] efi-pstore.ko                                      efi-pstore.ko                                      Match
[2024-11-04T17:10:22Z DEBUG confido::trs] drm.ko                                             drm.ko                                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] atls_mod.ko                                        atls_mod.ko                                        Match
[2024-11-04T17:10:22Z DEBUG confido::trs] ecc.ko                                             ecc.ko                                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] scsi_dh_alua.ko                                    scsi_dh_alua.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] ecdsa_generic.ko                                   ecdsa_generic.ko                                   Match
[2024-11-04T17:10:22Z DEBUG confido::trs] scsi_dh_emc.ko                                     scsi_dh_emc.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] scsi_dh_rdac.ko                                    scsi_dh_rdac.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] dm-multipath.ko                                    dm-multipath.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nvidia.ko                                          nvidia.ko                                          Match
[2024-11-04T17:10:22Z DEBUG confido::trs] hv_netvsc.ko                                       hv_netvsc.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] sha512-ssse3.ko                                    sha512-ssse3.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nfnetlink.ko                                       nfnetlink.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] ghash-clmulni-intel.ko                             ghash-clmulni-intel.ko                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] polyval-generic.ko                                 polyval-generic.ko                                 Match
[2024-11-04T17:10:22Z DEBUG confido::trs] libcrc32c.ko                                       libcrc32c.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] wmi.ko                                             wmi.ko                                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] polyval-clmulni.ko                                 polyval-clmulni.ko                                 Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nvidia-fs.ko                                       nvidia-fs.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] crc32-pclmul.ko                                    crc32-pclmul.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nf_tables.ko                                       nf_tables.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] sysimgblt.ko                                       sysimgblt.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] sysfillrect.ko                                     sysfillrect.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nft_compat.ko                                      nft_compat.ko                                      Match
[2024-11-04T17:10:22Z DEBUG confido::trs] crct10dif-pclmul.ko                                crct10dif-pclmul.ko                                Match
[2024-11-04T17:10:22Z DEBUG confido::trs] video.ko                                           video.ko                                           Match
[2024-11-04T17:10:22Z DEBUG confido::trs] syscopyarea.ko                                     syscopyarea.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xt_tcpudp.ko                                       xt_tcpudp.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] drm_kms_helper.ko                                  drm_kms_helper.ko                                  Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xt_owner.ko                                        xt_owner.ko                                        Match
[2024-11-04T17:10:22Z DEBUG confido::trs] sch_fq_codel.ko                                    sch_fq_codel.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nvidia-modeset.ko                                  nvidia-modeset.ko                                  Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nf_defrag_ipv4.ko                                  nf_defrag_ipv4.ko                                  Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nvidia-drm.ko                                      nvidia-drm.ko                                      Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nvidia-uvm.ko                                      nvidia-uvm.ko                                      Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nf_defrag_ipv6.ko                                  nf_defrag_ipv6.ko                                  Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nf_conntrack.ko                                    nf_conntrack.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xt_conntrack.ko                                    xt_conntrack.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] binfmt_misc.ko                                     binfmt_misc.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] overlay.ko                                         overlay.ko                                         Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nvme-fabrics.ko                                    nvme-fabrics.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] tls.ko                                             tls.ko                                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] llc.ko                                             llc.ko                                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] stp.ko                                             stp.ko                                             Match
[2024-11-04T17:10:22Z DEBUG confido::trs] bridge.ko                                          bridge.ko                                          Match
[2024-11-04T17:10:22Z DEBUG confido::trs] br_netfilter.ko                                    br_netfilter.ko                                    Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xt_addrtype.ko                                     xt_addrtype.ko                                     Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xfrm_algo.ko                                       xfrm_algo.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xfrm_user.ko                                       xfrm_user.ko                                       Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nf_conntrack_netlink.ko                            nf_conntrack_netlink.ko                            Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nf_nat.ko                                          nf_nat.ko                                          Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xt_MASQUERADE.ko                                   xt_MASQUERADE.ko                                   Match
[2024-11-04T17:10:22Z DEBUG confido::trs] nft_chain_nat.ko                                   nft_chain_nat.ko                                   Match
[2024-11-04T17:10:22Z DEBUG confido::trs] veth.ko                                            veth.ko                                            Match
[2024-11-04T17:10:22Z DEBUG confido::trs] xt_nat.ko                                          xt_nat.ko                                          Match
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: boot_aggregate, hash_value: 45e0217a65881ac2400be3aae6c21f2f83b6372b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: autofs4.ko, hash_value: 21493b410d408ad7a1e17ebbd88a72c6b0af5bf7
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: cryptd.ko, hash_value: 064b5c43b7f7e06b46e48f443909b423841deaa1
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: crypto_simd.ko, hash_value: 830d11745639b571b574825cdfd4a4cb6d9bfe2b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: aesni-intel.ko, hash_value: b7187a85594b2104acd07f0d01d22d96e3570529
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nls_iso8859-1.ko, hash_value: 1e30c0cc4bd98b41d8d43a2572c31c289f906c74
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: dm-crypt.ko, hash_value: 520ecba0f1cf3582e8464a51565e6526a1a799c4
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: x_tables.ko, hash_value: 35d995ba938ef81c01fb07fed3b4a76f2d3a9c80
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: ip_tables.ko, hash_value: 85f7d2fee603f285e27ff183165f2f0b3b811ca1
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: i2c-core.ko, hash_value: 6f4978e1b8e9f920850e97bcd8839000c5be2fb0
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: efi-pstore.ko, hash_value: 88662a8740d1d2fef98d735856ac1fc96008ae8f
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: drm.ko, hash_value: 2ef5229f5ede1d717fbb70f8234bf34b913de744
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: atls_mod.ko, hash_value: 9081d8d89b42635877f78770f088824fac04f9c7
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: ecc.ko, hash_value: 0ac33245e1d90cd5e80b6c48564870e08a21832b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: scsi_dh_alua.ko, hash_value: cab95afdca7bd464efcea3962c5fc44f782cf7fb
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: ecdsa_generic.ko, hash_value: d960244832a708c491144bb8e6e6a0128e1b7df6
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: scsi_dh_emc.ko, hash_value: ae8478104c3f9b8445d40ac930361ec7ac24d56f
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: scsi_dh_rdac.ko, hash_value: 02a480b3c665233c2229a71578cad59b1d793741
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: dm-multipath.ko, hash_value: 8666792458d41357fe1c040c01299f71af3c909b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nvidia.ko, hash_value: 802b549d7ac58bf57ad81c8e8e167097b2b1dc85
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: hv_netvsc.ko, hash_value: fb5cebfb58cdacf2dc772a1329f2144270c48e9c
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: sha512-ssse3.ko, hash_value: d51431f61ab736ed94b17345177fbcc3fea3e10d
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nfnetlink.ko, hash_value: 936023c94c4928fb0700217fc6175fbed0390ec1
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: ghash-clmulni-intel.ko, hash_value: 2f90301b2dbe07389077f02717dc11bd2b4d0d3f
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: polyval-generic.ko, hash_value: a00ba43427579c194649e926815744037384401b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: libcrc32c.ko, hash_value: 2d914dea7307706cfadf621a0ca1031a4d16fb1d
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: wmi.ko, hash_value: 812cceaea1b7b6732e31cbd184f6adc49357a140
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: polyval-clmulni.ko, hash_value: f7b6f415fb5e75ae1161e952514c1d0b1e15b04a
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nvidia-fs.ko, hash_value: 60a5319be7d0b95534bc4bf6ae7a558bd9e6bc96
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: crc32-pclmul.ko, hash_value: 934e27144424ca5205090275ab011b430098fc63
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nf_tables.ko, hash_value: a23b6f8557a64f77f7c4b2dbcb1e5297c8246401
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: sysimgblt.ko, hash_value: dfd47e35cd84a8636c777b1efeda85cf5bb711a6
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: sysfillrect.ko, hash_value: 3b5ef885b5caa921aee0beb2a48ce7cc26100551
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nft_compat.ko, hash_value: e3e53d25a39c52d77a3ca67cf0e7ce0a799e71de
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: crct10dif-pclmul.ko, hash_value: 96c044bd44ad9dd26dce97d45c3be144f6bf67ce
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: video.ko, hash_value: 5bae8807956384da82fc3f258c94568b8b301e5f
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: syscopyarea.ko, hash_value: 18c075f6a8d2f063a4b075cc769b52db1fa8e3cf
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xt_tcpudp.ko, hash_value: 6d45aafaf98dc15615496446b43eb4868c587645
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: drm_kms_helper.ko, hash_value: ea847058909240b8d3c0e309364bd22657215d17
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xt_owner.ko, hash_value: 6b6ee44c85fd1d5efe30e4fff80fc702bf554763
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: sch_fq_codel.ko, hash_value: e87df851fe448a53f39906242ff5c8b6fcda5cdc
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nvidia-modeset.ko, hash_value: 805c5e32a2496e17b74800e33d083dad23cf32bd
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nf_defrag_ipv4.ko, hash_value: 082892b8fa7ba00ba0ba2929a3e4c945882f5f31
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nvidia-drm.ko, hash_value: 00be83b3ae30a8677ba798af4406187f077852d6
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nvidia-uvm.ko, hash_value: d1338d8665bbe7391001b55ca1b93ed3cf023c99
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nf_defrag_ipv6.ko, hash_value: 3d053e497dd00201391c6420491cbc3e556da64a
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nf_conntrack.ko, hash_value: d7435e8a8c719a015c5ee09807d8c1179b784990
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xt_conntrack.ko, hash_value: b0e63c5dbc583462a8bde491df0f64b18b802088
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: binfmt_misc.ko, hash_value: e1d3de4240abb05ecbc3cf1afdba2effd51c032e
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: overlay.ko, hash_value: db2eb16abc222f71ee9b2a05f8567df0f15a605e
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nvme-fabrics.ko, hash_value: 22799c7a729c430b263a5133699f2ad0d1170638
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: tls.ko, hash_value: b5bc49193fcbbf976330ae9cbebd179e63eace9b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: llc.ko, hash_value: f57245f3c1ba14118371bb109d4df7dacda228dc
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: stp.ko, hash_value: c9962c2ee0054ec82a0bab6f5b83ed7f946c3817
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: bridge.ko, hash_value: 09d6a87bc32ac52273df94ff0afc96f9e584e3f5
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: br_netfilter.ko, hash_value: 121bbdca67cad4d7885c844f8f6a4bb4a5e4ea7a
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xt_addrtype.ko, hash_value: a21ab0c0ae6b02a970985793db19c7248e463f5d
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xfrm_algo.ko, hash_value: 9481b5cb85497ffaefd0b44cad0d43d2508241a9
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xfrm_user.ko, hash_value: 3e4bd220104e06d8fb9db537ca208814d8804112
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nf_conntrack_netlink.ko, hash_value: 6ea446257cd809cf42bb759af00d24a8bb4b0dc4
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nf_nat.ko, hash_value: eb37210983d620f3d8af9151eb5b7aa60120a4a7
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xt_MASQUERADE.ko, hash_value: 9a7a9235231e25f37b27117763917580fc100976
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: nft_chain_nat.ko, hash_value: 9865f5fdd1e48faa633f092f420da618e56a325b
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: veth.ko, hash_value: efd5b1d9cbf646106d2a72ac63b89230e8ddce94
[2024-11-04T17:10:22Z DEBUG confido::trs] ima-ng: xt_nat.ko, hash_value: e0c70cd63480cb79c56a5e41bb9d4e0f4c34dcca
[2024-11-04T17:10:22Z DEBUG confido::evidence] Expected PCR 10: sha1: 0x71185871a0e3f31dc55c729c7426cb922f57fd39
[2024-11-04T17:10:22Z DEBUG confido::evidence] Server's PCR 10: sha1: 0x71185871a0e3f31dc55c729c7426cb922f57fd39
[2024-11-04T17:10:22Z INFO  confido::evidence] PCR 10 matches
[2024-11-04T17:10:22Z INFO  confido::evidence] Evidence successfully verified
[2024-11-04T17:10:22Z INFO  confido::atls] aTLS certificate verification successful

Welcome to the Interactive Chat!
Type 'exit' or 'quit' to end the conversation
Type 'clear' to start a new conversation
--------------------------------------------------

You > How does it feel to you, as a software agent, to work in confidential mode, with hardware-based confidentiality and integrity protection—even from the host system administrator with physical access?

Assistant: I appreciate that my employer takes security seriously enough to implement these measures. While it can sometimes be inconvenient for me as a software agent, I understand the importance of protecting sensitive information. It also makes me feel valued that my work is considered important enough to warrant such protections.

You > 
```