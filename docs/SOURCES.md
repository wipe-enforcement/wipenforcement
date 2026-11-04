# Source register

Every figure in this repository that is not produced by the code itself, with its
date and its provenance. The platform's rule — *nothing is a number without a
source and a collection timestamp* — applies to the design documents too.

Third-party visit figures are **scale context**, never measurements of this
platform. They come from rights-holder filings against interested parties and are
contested in substance; they are cited to show the orders of magnitude involved,
and no figure in any report this system emits derives from them.

## Filings and enforcement records

| # | Fact | Source | Date |
|---|---|---|---|
| 1 | MBC Group: **350+ pirate websites launched since 2014**; MENA Anti-Piracy Coalition working with the MPAA | MPA/MBC submission to USTR, `downloads.regulations.gov/USTR-2018-0027-0021/attachment_1.pdf` | 2018 |
| 2 | beIN / 4K submission: **Laroza 7M+** monthly visits; **WeCima (successor to MyCima) 18M**; **Fasel/Faselplus 30M**; **Shahid4u 68,000 series, ~4M** | `downloads.regulations.gov/USTR-2024-0013-0037/attachment_1.pdf` | 2024 |
| 3 | ACE + Egyptian authorities shut down **Shahed4U**: 68,000 series, 18,700 films, **155M monthly visits, 118+ domains**; traffic from Egypt and Saudi Arabia; followed Egybest and MyCima takedowns | `alliance4creativity.com/de/news/ace-joins-forces-with-egyptian-authorities-...`; `egyptindependent.com` | 2024 |
| 4 | ACE + Egypt shut down the **Livehd7** live-sports ring, **85+ domains**; part of a MENA series including Laroza and Cima4U | `wire.expertini.com` (ACE press release syndication) | 2024-10-31 |
| 5 | UAE Ministry of Economy with TDRA blocked **1,117 websites** infringing IP rights, incl. an "InstaBlock" immediate-blocking initiative, protecting MBC, OSN and beIN | Korean IP Office report citing UAE MoE, `kipo.go.kr` BUT0000049 | 2024/2025 |
| 6 | MPA notorious-markets profiling of illegal IPTV: **Atlas Pro** (suspected Algerian), **Apollo Group TV**, **EVPad**, **GenIPTV**, **Gogo/Orca IPTV** (Algeria), **Kemo Lemo IPTV** (UAE, Dubai Police investigation) | MPA submission to USTR public consultation, via `torrentfreak.com/images/26.6-MPA_Submission.pdf` | 2026 |
| 7 | MPA on **piracy-as-a-service**: Vidsrc, XPass.top, HydraHD, **WHMCS Smarters** — "pirate sites and IPTV operators build off-the-shelf streaming operations" | `torrentfreak.com/images/mpa-ustr-26.pdf` | 2026 |
| 8 | UAE legal frame: Decree-Law 38/2021; IIPA recommends ISP mechanisms to disable access to structurally infringing sites | `iipa.org` 2025 Special 301 UAE country chapter; `iipa.org/files/uploads/2025/11/IIPA-Comments-for-the-2026-NTE-FINAL.pdf` | 2025 |

## MyCima → WeCima rotation (the basis of `qarin.discover`)

| # | Fact | Source | Date |
|---|---|---|---|
| 9 | MyCima: **Alexandria**-based, **~12,000 movies / ~26,000 series**, **~50m visits/month**; shut down by Egypt/ACE, reappeared **within days** as WeCima on `wecima.tube`, with dozens of near-identical domains registered as rotation stock | TorrentFreak, "Huge Piracy Site Killed By Egypt Gets Sewn Back To Life Like Osiris" (`torrentfreak.com/...-230302`), with syndicated copies at `mov.im` and `lj.rossia.org` | 2023-03 |
| 10 | Rotating domains observed: **`myciiima.autos`, `.bond`, `.boats`, `.makeup`, `.monster`** — ~70 in circulation; **`weciima.*` pre-registered as backups**; `myciiima.autos` at **43.3m monthly visits** | same TorrentFreak report, via syndicated copies | 2023-03 |
| 11 | `mycima.codes`: **freshly registered (22 days old)** mirror, part of the brand's "endless mirror chain using cheap TLDs, Cloudflare hosting and ad-network monetization" | `tools.malwaretips.com/url-scan/mycima.codes` | 2026 |
| 12 | `eegebest.com` (lookalike) keyword metadata **clusters the whole Arabic streaming brand family** — egybest, mycima, wecima, cima4u, arabseed, akwam, faselhd — "showing how successor sites inherit competitor brand names for search traffic" | SEO report `maximumseotools.com/resources/pdf-reports/eegebest.com_221266.pdf` | 2026 |
| 13 | WeCima marketed explicitly as **"بديل ماي سيما"** (the alternative to MyCima) and as the heir to EgyBest's audience while EgyBest was down; absorbed Ramadan content | `safa.ps` Arabic posts (2 posts, Feb 2023) | 2023-02 |
| 14 | MyCima and WeCima names **used together in page titles/descriptions by successor operators**; large shared libraries | Arabic blog post, `tumblr.com/m7eetcom` | 2023 |

## The supply side's own search grammar (the basis of `build_probes`)

| # | Fact | Source | Date |
|---|---|---|---|
| 15 | Page titles follow **"اسم الفيلم + السنة + مدبلج + HD أون لاين + أسماء مواقع المشاهدة (ماي سيما، شاهد فور يو، عرب سيد) للظهور في نتائج البحث"**; the network uses keyword sets like "مدبلج HD أون لاين", "مترجم عربي", "1080p BluRay" | `larroza.homes/video.php?vid=bde8c70bd` and `larroza.quest/video.php?vid=0ae633027` — the sites' own meta descriptions | 2026 |
| 16 | Arabic film-page keyword vocabulary in the wild: "مشاهدة وتحميل", "مترجم كامل HD", "جودة اتش دي", "بلوراي", "فيلم كامل", "مدبلج عربي", "بث عبر الإنترنت", "تحميل UHD", "1080p", "العنوان الفرعي بالعربية", "دقة 720p/1080p", "دفق كامل اون لاين كامل تحميل UHD بوكس اوفيس" | Observed across Blogspot/UGC spam layers: `waterpiksensonicreviews.blogspot.com`, `caughtonlomo.blogspot.com`, `sprinkledconfetti.blogspot.com`, `mye-sweetest-life.blogspot.com`, `its-time-to-let-it-go.blogspot.com`, `quefemdelcaldo.blogspot.com` | 2017–2020 |
| 17 | A distinct **SEO parasite layer** exists: free-hosted pages repeating the Arabic keyword vocabulary "دون محتوى فعلي" (with no actual content), purely to capture and redirect search traffic | same, described in situ | 2017–2020 |
| 18 | Arabic "best free movie sites" **listicle layer** on mainstream content sites names the pirate brands directly: السينما كوم, فيديو لاروزا, أكوام, إيجي بست, سيما 4u, عرب سيد, دراما كافيه, فاصل إتش دي, قصة عشق, أهواك تي في, ماي سيما, برستيج, سيما كلوب, أفلامكو, إيجي شير, عرب ليونز, وقت الأفلام, HiTV, HDPopcorns, وياك, شوف أفلام | `alsumaria.tv` (tech article), `elbalad.news`, `iwebtv.app/popular-video-websites/ar` and `/ar-sa`, `rvewx.com/tags/*`, `shoofaflam.tv` | 2026 |
| 19 | **A third party publishes a per-country ranking of pirate video sites** (`iWebTV` "popular video websites", with separate Arabic and Saudi editions, refreshed daily) — a ready-made ranked lexicon available without any crawling | `iwebtv.app/popular-video-websites/ar`, `/ar-sa`; `webtvapp.swishly.com/popular/ar-sa.html` | 2026 |
| 20 | Community-maintained **open piracy indices** catalogue non-English streaming resources including Arabic sites | `github.com/fmhy` `docs/non-english.md` | 2026 |
| 21 | Arabic **m3u playlists circulate in plaintext** on paste hosts (e.g. `178.32.255.199:1935/live/ifilmar/chunklist` with Al Hurra, Al Arabiya, Al Mayadeen, Saudi TV) — the IPTV surface is readable without any special access | pastebin raw, surfaced by search | 2026 |
| 22 | A documented **UGC-discovery method** exists: `zerodollarmovies.com` wraps the YouTube API to locate complete films, "ويحل مشكلة تشتت النتائج وعدم اكتمال الأفلام" | Arabic tech-blog articles, `wahat-tq.blogspot.com`, `itprofessional12.blogspot.com` | 2014 |

## Market context (unchanged from earlier research)

| # | Fact | Source | Date |
|---|---|---|---|
| 23 | MENA SVOD: **Shahid 4.4M**, **YouTube Premium 3.7M**, **Netflix 3.0M**, **STARZPLAY 2.3M** subscribers | Omdia, via BusinessWire | 2024-12 / 2025-05-13 |
| 24 | Shahid VIP + OSN+ + Disney+ bundled as a regional offering | 3Vision | 2026-03-06 |
| 25 | **85%** of live-event piracy hosted offshore/non-compliant; **66%** of takedown notices ignored entirely, only **11%** suspend streams; **90%** of illegal streams reappear within 24h; **6%** of notices answered inside the 30-minute live window | AAPA (Anti-Arabic-Piracy Alliance) submission | 2026-05 |

Note on #25: the 90%-within-24-hours reappearance figure and the rotation findings
(#9–#14) are the same phenomenon measured at two different scales, and
`reappearance_latency` is the instrument that measures it per-offering rather than
per-industry.

## What is *not* cited

Nothing in `qarin/` derives a published number from the sources above. They
establish that the ecosystem has the shape the code assumes — brands, rotation,
a keyword grammar, a per-country public ranking. Every figure the platform
reports is either a receipt it took itself or an arithmetic over such receipts.
