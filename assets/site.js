"use strict";
document.documentElement.classList.replace("no-js", "js");

const translations = {
  en: {
    titles: {
      home: "WIPE — Evidence you can replay",
      method: "WIPE — Method and evidence",
      radar: "WIPE — Public measurement status",
      report: "WIPE — Public reports",
      verify: "WIPE — Rightsholder pilot",
      governance: "WIPE — Privacy and governance"
    },
    home: {
      nav_home: "Overview",
      nav_method: "Method",
      nav_radar: "Measurement status",
      nav_report: "Reports",
      nav_verify: "Rightsholder pilot",
      brand_subtitle: "Rights-aware evidence",
      brand_label: "WIPE home",
      nav_aria: "Primary navigation",
      language_label: "Switch language to Arabic",
      language_button: "العربية",
      home_kicker: "A clearer record for Arabic and MENA screen works",
      signal_aria: "Interactive evidence path illustration",
      signal_title: "An illustrative evidence path",
      signal_desc: "A public observation connects to provenance and a human review gate. This is a conceptual illustration, not a live system.",
      stage_group: "Evidence path stages",
      wire_observe: "OBSERVE",
      wire_verify: "VERIFY",
      wire_review: "REVIEW",
      hero_title: "Evidence you can replay. Decisions you can defend.",
      hero_lede: "WIPE is being built for rights holders who need a clearer view of publicly observable offers of Arabic and MENA audiovisual works. It connects a source, a rights context, and a reviewable record—without pretending that a listing reveals its audience or financial impact.",
      hero_primary: "See how the method works",
      hero_secondary: "Discuss a rightsholder pilot",
      hero_status: "Current status: no production sources are connected. This site publishes no live piracy measurements.",
      frame_title: "Signal path · interactive model",
      frame_state: "Illustrative · not live data",
      stage_observe: "01 · Observe",
      stage_provenance: "02 · Verify",
      stage_review: "03 · Review",
      stage_observe_detail: "Begin with a publicly visible offer. An absent observation is not proof that no offer exists.",
      stage_provenance_detail: "Keep source, capture time, rights context, and uncertainty attached to the record.",
      stage_review_detail: "A rightsholder reviews evidence before any enforcement workflow is considered.",
      overview_title: "A signal is a starting point—not a verdict.",
      overview_copy: "The platform is designed to make the distance between a public observation and a responsible decision visible. Each step can be checked, corrected, or declined.",
      step_observe_title: "Record what is visible",
      step_observe_copy: "Describe a public offer and its source. Do not infer viewers, intent, or ownership from a single trace.",
      step_context_title: "Add verified rights context",
      step_context_copy: "A work, territory, authorised channel, and licence window need an accountable source.",
      step_review_title: "Invite independent review",
      step_review_copy: "Keep uncertainty explicit and give the rightsholder a path to correct or dispute a record.",
      step_action_title: "Support authorised action",
      step_action_copy: "Enforcement support is a future, permissioned workflow—not a claim that the site can issue takedowns today.",
      market_title: "Start where the work is understood.",
      market_eyebrow: "Scope · proposed, not measured",
      market_copy: "The owner’s proposed rollout begins with Saudi Arabia, then expands through the named markets. This is a planning sequence, not a ranking and not measured coverage.",
      market_ksa: "Saudi Arabia",
      market_uae: "United Arab Emirates",
      market_egypt: "Egypt",
      market_kuwait: "Kuwait",
      market_lebanon: "Lebanon",
      market_iraq: "Iraq",
      market_morocco: "Morocco",
      market_levant: "Levant cluster",
      market_planned: "Planned · not measured",
      market_first: "Initial focus · not measured",
      market_note: "The current codebase declares a different ten-market baseline. Market scope must be reconciled with the owner and local advisors before it is represented as an operating plan.",
      service_title: "Build with rightsholders—not from a guessed ranking.",
      service_copy: "The initial service shortlist is a scoping input, not a ranking, endorsement, or allegation. Every service, title, and territory needs a dated source and rights-holder validation before public measurement.",
      shortlist_shahid: "Shahid / MBC Group",
      shortlist_watchit: "WATCH IT",
      shortlist_yango: "Yango Play",
      shortlist_starz: "STARZPLAY",
      shortlist_other: "Other Arabic and regional services",
      shortlist_state: "Owner-proposed candidate · not a ranking",
      horizon_title: "Designed to grow without hiding uncertainty.",
      horizon_copy: "The ten-year direction is a system that can adapt as platforms, policy, and AI change without changing what a metric means. Each step depends on evidence quality, human review, and operating permission—not a forecast or promise of autonomous growth.",
      horizon_now_title: "Establish a trustworthy pilot",
      horizon_now_copy: "Agree the source, rights scope, review process, and privacy terms with a small number of rightsholders. Publish no live figure until the collection and validation gates pass.",
      horizon_next_title: "Expand by proven coverage",
      horizon_next_copy: "Add independent sources market by market; document gaps, failures, retention, and corrections. Keep the public view separate from private monitoring intelligence.",
      horizon_long_title: "Scale with accountable automation",
      horizon_long_copy: "Use replaceable connectors, portable records, tested recovery, and human approval for consequential action. AI may help triage; it does not self-authorise collection, accusation, or enforcement.",
      contact_title: "Start with one title and one territory.",
      contact_copy: "A focused conversation can define a safe pilot, the evidence a rightsholder needs, and what must remain private.",
      contact_button: "Contact WIPE",
      footer_statement: "Rights-aware measurement and evidence for Arabic and MENA audiovisual content.",
      footer_legal: "Public observations are not legal findings. This website is a product preview; it does not provide legal advice or claim a live collection service.",
      footer_privacy: "Privacy and governance"
    },
    method: {
      page_label: "How the evidence is meant to work",
      page_title: "Make each claim smaller, clearer, and easier to check.",
      page_lede: "WIPE separates what was observed from what is inferred. Public visibility, rights status, audience records, and enforcement outcomes are different evidence—not interchangeable numbers.",
      method_observe_title: "Observe, with permission and limits",
      method_observe_copy: "A source is assessed before use for purpose, terms, robots guidance, rate limits, privacy impact, retention, and an accountable operator. The repository does not currently have a production source configured.",
      method_evidence_title: "Keep provenance with the record",
      method_evidence_copy: "A measurement should state what it counts, where and when it was collected, the method used, its coverage, and known limitations. If those fields are missing, the output stays unknown.",
      method_rights_title: "Separate observation from rights conclusions",
      method_rights_copy: "A public offer may warrant review, but it does not by itself prove infringement, ownership, intent, damages, or a particular legal remedy. A verified rights calendar and human review are required.",
      method_private_title: "Protect operational intelligence",
      method_private_copy: "Public pages explain the evidence standard, not private watchlists, detection patterns, source credentials, or collection thresholds. Sensitive operational details belong in a properly secured, authorised partner workflow.",
      method_unit_title: "Define what one observation means",
      method_unit_copy: "A count should name its unit—for example, one work, service, country, and observation window—and explain how duplicate listings are treated.",
      method_coverage_title: "Show coverage beside the count",
      method_coverage_copy: "State which public surfaces, languages, queries, and dates were checked, as well as gaps, failed checks, and markets not observed. A detected count is not a complete universe.",
      method_correction_title: "Make correction part of the record",
      method_correction_copy: "A review route should cover mistaken matches, licensed use, and territory or window differences. Preserve corrections and unresolved disputes alongside confirmed observations.",
      method_unknown_title: "Unknown is a valid result",
      method_unknown_copy: "No feed, stale data, weak coverage, conflicting rights records, or missing provenance must never be rendered as zero, a clean bill of health, or a confident accusation.",
      method_footer: "These are product principles, not a legal opinion or a claim that production controls are already deployed."
    },
    radar: {
      page_label: "Public measurement status",
      page_title: "No live measurements are published.",
      page_lede: "WIPE will show a number only after its source, collection time, method, and review status are available. At present, the repository does not identify a healthy production feed or a public measurement snapshot.",
      radar_state: "UNMEASURED · NO PRODUCTION SNAPSHOT",
      radar_copy: "The empty state is intentional. It prevents an absent feed from looking like zero activity or a successful scan.",
      radar_what_title: "What must be true before publication",
      radar_gate_source: "A source has documented purpose, terms, access limits, and an accountable operator.",
      radar_gate_quality: "The collection is fresh, complete enough for its stated scope, and passes validation.",
      radar_gate_review: "A human reviewer approves the snapshot and confirms no private intelligence is exposed.",
      radar_gate_trace: "Each reported value links to a timestamp, method, and provenance record.",
      radar_contact: "Ask about a measured pilot"
    },
    report: {
      page_label: "Public reports",
      page_title: "No public edition has been released.",
      page_lede: "A report should be published only when its scope, sources, method, review, and limitations can be independently understood. No validated public edition is present in this repository.",
      report_state: "NO EDITION PUBLISHED",
      report_copy: "This page will link to dated editions and their correction history when a report passes the publication gate. Until then, it contains no placeholder figures or simulated results.",
      report_method: "Read the measurement principles"
    },
    verify: {
      page_label: "Rightsholder pilot",
      page_title: "Build the review process together.",
      page_lede: "The private review portal is not launched. WIPE is seeking structured feedback from content owners on evidence quality, rights context, corrections, and the boundaries that make a pilot trustworthy.",
      verify_state: "PILOT DISCUSSION · NO PRIVATE PORTAL",
      verify_copy: "Do not send confidential titles, audience exports, credentials, or enforcement intelligence through this public site or an ordinary email. A secure, approved intake must be agreed before any sensitive material is shared.",
      verify_steps_title: "What a responsible pilot defines",
      verify_step_scope: "One rightsholder, a clearly scoped work and territory, and named authorised users.",
      verify_step_sources: "Approved public sources, terms and privacy review, retention, and an operator responsible for failures.",
      verify_step_review: "A way to inspect, correct, or dispute each record before any action.",
      verify_step_exit: "A documented stop, deletion, incident, and handover process.",
      verify_contact: "Discuss a pilot without sharing confidential data"
    },
    governance: {
      page_label: "Privacy and governance",
      page_title: "A public site is not permission to collect.",
      page_lede: "The legal and privacy position depends on the source, data, purpose, jurisdiction, and deployment. This page states the safeguards WIPE must establish; it is not legal advice or a compliance certification.",
      governance_site_title: "This website",
      governance_site_copy: "This static site does not provide a login, accept files, or publish a live collection feed. It stores the chosen language in the browser so the site can remember English or Arabic. No analytics or external font service is included in this implementation.",
      governance_sources_title: "Before a source is used",
      governance_sources_copy: "Review the source’s terms, robots directives, access controls, permitted rate, personal-data exposure, purpose, retention, and applicable local law. Record the decision, reviewer, and date. A public URL alone does not establish permission.",
      governance_evidence_title: "Before a finding is shared",
      governance_evidence_copy: "Minimise data, separate public observations from rightsholder-supplied records, restrict access by role, preserve correction history, and avoid publishing information that could expose a person or private monitoring operation.",
      governance_law_title: "Local review is required",
      governance_law_copy: "Before collection or evidence use in any market, qualified local counsel must review the applicable privacy, copyright, evidence, cross-border transfer, and intermediary rules. The site does not determine legality or guarantee admissibility.",
      governance_contact: "Ask about governance for a pilot"
    }
  },
  ar: {
    titles: {
      home: "وايب — أدلة قابلة لإعادة الفحص",
      method: "وايب — المنهج والأدلة",
      radar: "وايب — حالة القياس العام",
      report: "وايب — التقارير العامة",
      verify: "وايب — تجربة أصحاب الحقوق",
      governance: "وايب — الخصوصية والحوكمة"
    },
    home: {
      nav_home: "الرئيسية",
      nav_method: "المنهج",
      nav_radar: "حالة القياس",
      nav_report: "التقارير",
      nav_verify: "تجربة أصحاب الحقوق",
      brand_subtitle: "أدلة تراعي الحقوق",
      brand_label: "الصفحة الرئيسية لوايب",
      nav_aria: "التنقل الرئيسي",
      language_label: "تغيير اللغة إلى الإنجليزية",
      language_button: "English",
      home_kicker: "سجل أوضح للأعمال العربية والإقليمية",
      signal_aria: "رسم توضيحي تفاعلي لمسار الأدلة",
      signal_title: "مسار توضيحي للأدلة",
      signal_desc: "يربط الرصد العلني بمصدره وبوابة مراجعة بشرية. هذا رسم مفاهيمي وليس نظاماً مباشراً.",
      stage_group: "مراحل مسار الأدلة",
      wire_observe: "رصد",
      wire_verify: "تحقق",
      wire_review: "مراجعة",
      hero_title: "أدلة يمكن إعادة فحصها. وقرارات يمكن الدفاع عنها.",
      hero_lede: "تعمل وايب على بناء منصة لأصحاب الحقوق تمنحهم رؤية أوضح للعروض المتاحة علناً للأعمال السمعية والبصرية العربية والإقليمية. تربط المنصة بين المصدر وسياق الحقوق وسجل قابل للمراجعة، من دون افتراض أن ظهور عرض ما يكشف عدد جمهوره أو أثره المالي.",
      hero_primary: "تعرّف على المنهج",
      hero_secondary: "ناقش تجربة لأصحاب الحقوق",
      hero_status: "الحالة الحالية: لا توجد مصادر تشغيلية متصلة، ولا تنشر هذه الصفحة قياسات مباشرة للقرصنة.",
      frame_title: "مسار الإشارة · نموذج تفاعلي",
      frame_state: "توضيحي · ليس بيانات مباشرة",
      stage_observe: "١ · رصد",
      stage_provenance: "٢ · تحقق",
      stage_review: "٣ · مراجعة",
      stage_observe_detail: "تبدأ العملية بعرض ظاهر للعموم. وغياب الرصد لا يثبت غياب العروض.",
      stage_provenance_detail: "يرتبط بالسجل مصدره ووقت التقاطه وسياق الحقوق وحدود اليقين.",
      stage_review_detail: "يراجع صاحب الحق الأدلة قبل النظر في أي مسار إنفاذ.",
      overview_title: "الإشارة نقطة بداية، وليست حكماً.",
      overview_copy: "صُممت المنصة لتُظهر المسافة بين الرصد العلني والقرار المسؤول. ويمكن التحقق من كل خطوة أو تصحيحها أو رفضها.",
      step_observe_title: "تسجيل ما يظهر للعموم",
      step_observe_copy: "توثيق عرض ظاهر ومصدره، من دون استنتاج عدد المشاهدين أو النية أو الملكية من أثر واحد.",
      step_context_title: "إضافة سياق حقوق موثّق",
      step_context_copy: "يتطلب العمل والإقليم والقناة المرخصة ونافذة الترخيص مصدراً يمكن مساءلته.",
      step_review_title: "إتاحة مراجعة مستقلة",
      step_review_copy: "إبقاء حدود اليقين واضحة وتمكين صاحب الحق من تصحيح السجل أو الاعتراض عليه.",
      step_action_title: "دعم إجراء مصرح به",
      step_action_copy: "دعم الإنفاذ مسار مستقبلي يخضع للتفويض والمراجعة، وليس ادعاءً بأن الموقع يرسل طلبات إزالة اليوم.",
      market_title: "نبدأ من حيث نفهم طبيعة المحتوى.",
      market_eyebrow: "النطاق · مقترح وليس مقاساً",
      market_copy: "يبدأ ترتيب التوسع المقترح من المالك بالسعودية، ثم الأسواق المذكورة. هذا تسلسل تخطيطي، وليس ترتيباً للأسواق أو تغطية مقاسة.",
      market_ksa: "السعودية",
      market_uae: "الإمارات العربية المتحدة",
      market_egypt: "مصر",
      market_kuwait: "الكويت",
      market_lebanon: "لبنان",
      market_iraq: "العراق",
      market_morocco: "المغرب",
      market_levant: "مجموعة بلاد الشام",
      market_planned: "مخطط · غير مقاس",
      market_first: "نطاق البداية · غير مقاس",
      market_note: "يعرّف الكود الحالي نطاقاً أساسياً مختلفاً من عشرة أسواق. يجب التوفيق بين نطاق الأسواق والمالك والمستشارين المحليين قبل عرضه كخطة تشغيلية.",
      service_title: "نبني مع أصحاب الحقوق، لا وفق ترتيب مفترض.",
      service_copy: "القائمة الأولية للخدمات مدخل لتحديد النطاق، وليست ترتيباً أو تزكية أو اتهاماً. ويلزم التحقق من مصدر مؤرخ ومراجعة صاحب الحق لكل خدمة وعمل وإقليم قبل نشر أي قياس.",
      shortlist_shahid: "شاهد / مجموعة MBC",
      shortlist_watchit: "WATCH IT",
      shortlist_yango: "Yango Play",
      shortlist_starz: "STARZPLAY",
      shortlist_other: "خدمات عربية وإقليمية أخرى",
      shortlist_state: "مرشح اقترحه المالك · ليس ترتيباً",
      horizon_title: "نمو يواكب الزمن من دون إخفاء عدم اليقين.",
      horizon_copy: "تتمثل الرؤية لعشر سنوات في نظام يتكيف مع تغير المنصات والسياسات والذكاء الاصطناعي من دون تغيير معنى المؤشر. وتعتمد كل خطوة على جودة الأدلة والمراجعة البشرية وإذن التشغيل، لا على توقع مؤكد أو وعد بالتوسع الذاتي.",
      horizon_now_title: "تأسيس تجربة موثوقة",
      horizon_now_copy: "الاتفاق مع عدد محدود من أصحاب الحقوق على المصدر ونطاق الحقوق وآلية المراجعة وشروط الخصوصية. لا تنشر أرقام مباشرة حتى اجتياز بوابات الجمع والتحقق.",
      horizon_next_title: "التوسع وفق تغطية مثبتة",
      horizon_next_copy: "إضافة مصادر مستقلة سوقاً بعد سوق، وتوثيق الفجوات والأعطال والاحتفاظ والتصحيحات. ويظل العرض العام منفصلاً عن معلومات الرصد التشغيلية الخاصة.",
      horizon_long_title: "التوسع بأتمتة خاضعة للمساءلة",
      horizon_long_copy: "استخدام موصلات قابلة للاستبدال وسجلات قابلة للنقل واستعادة مختبرة وموافقة بشرية قبل أي إجراء مؤثر. قد يساعد الذكاء الاصطناعي في الفرز، لكنه لا يفوض الجمع أو الاتهام أو الإنفاذ لنفسه.",
      contact_title: "نبدأ بعمل واحد وإقليم واحد.",
      contact_copy: "تساعد محادثة مركزة على تحديد تجربة آمنة والأدلة التي يحتاجها صاحب الحق وما يجب أن يبقى خاصاً.",
      contact_button: "تواصل مع وايب",
      footer_statement: "قياس وأدلة تراعي الحقوق للمحتوى السمعي والبصري العربي والإقليمي.",
      footer_legal: "الرصد العلني ليس حكماً قانونياً. الموقع معاينة للمنتج؛ ولا يقدم مشورة قانونية أو يدعي تقديم خدمة رصد مباشرة.",
      footer_privacy: "الخصوصية والحوكمة"
    },
    method: {
      page_label: "كيف ينبغي أن تعمل الأدلة",
      page_title: "كل ادعاء أوضح وأضيق وأسهل للتحقق.",
      page_lede: "تفصل وايب بين ما تم رصده وما تم استنتاجه. فالظهور العلني وحالة الحقوق وسجلات الجمهور ونتائج الإنفاذ أنواع مختلفة من الأدلة وليست أرقاماً قابلة للاستبدال.",
      method_observe_title: "الرصد بإذن وحدود واضحة",
      method_observe_copy: "يُقيّم المصدر قبل استخدامه من حيث الغرض والشروط وتوجيهات robots وحدود الطلبات وأثر الخصوصية والاحتفاظ والمسؤول التشغيلي. ولا يحتوي المستودع حالياً على مصدر إنتاج مهيأ.",
      method_evidence_title: "إبقاء مصدر السجل مع البيانات",
      method_evidence_copy: "يجب أن يوضح القياس ما يعدّه وأين ومتى جُمع والمنهج المستخدم ومدى التغطية والقيود المعروفة. وعند نقص هذه المعلومات تظل النتيجة غير معلومة.",
      method_rights_title: "فصل الرصد عن الاستنتاج القانوني",
      method_rights_copy: "قد يستدعي العرض العلني المراجعة، لكنه لا يثبت وحده الانتهاك أو الملكية أو القصد أو الضرر أو علاجاً قانونياً محدداً. ويلزم تقويم حقوق موثق ومراجعة بشرية.",
      method_private_title: "حماية المعلومات التشغيلية",
      method_private_copy: "تشرح الصفحات العامة معيار الأدلة، لا قوائم الرصد الخاصة أو أنماط الكشف أو بيانات الدخول للمصادر أو حدود الجمع. مكان التفاصيل التشغيلية الحساسة هو مسار شراكة مفوض ومؤمن على نحو ملائم.",
      method_unit_title: "تحديد معنى الرصد الواحد",
      method_unit_copy: "يجب أن يحدد العدد وحدته، مثل عمل واحد وخدمة وبلد ونافذة رصد، وأن يوضح طريقة التعامل مع العروض المكررة.",
      method_coverage_title: "إظهار التغطية بجوار العدد",
      method_coverage_copy: "يجب ذكر المصادر العامة واللغات وعبارات البحث والتواريخ التي شملها الفحص، إلى جانب الفجوات والأعطال والأسواق غير المرصودة. فالعدد المكتشف لا يمثل الكون الكامل.",
      method_correction_title: "اعتبار التصحيح جزءاً من السجل",
      method_correction_copy: "ينبغي أن تشمل المراجعة حالات الخطأ في المطابقة والاستخدام المرخص واختلاف الإقليم أو نافذة الترخيص، مع حفظ التصحيحات والنزاعات غير المحسومة بجوار الأرصاد المؤكدة.",
      method_unknown_title: "المجهول نتيجة مقبولة",
      method_unknown_copy: "لا يجوز تحويل انقطاع المصدر أو تقادمه أو ضعف التغطية أو تعارض سجلات الحقوق أو غياب المصدر إلى صفر أو شهادة سلامة أو اتهام واثق.",
      method_footer: "هذه مبادئ للمنتج وليست رأياً قانونياً أو ادعاءً بأن ضوابط التشغيل قد نُشرت بالفعل."
    },
    radar: {
      page_label: "حالة القياس العام",
      page_title: "لا توجد قياسات مباشرة منشورة.",
      page_lede: "لن تعرض وايب رقماً قبل إتاحة مصدره ووقت جمعه ومنهجه وحالة مراجعته. ولا يحدد المستودع حالياً مصدراً إنتاجياً سليماً أو لقطة قياس عامة.",
      radar_state: "غير مقاس · لا توجد لقطة إنتاج",
      radar_copy: "هذه الحالة الفارغة مقصودة، حتى لا يبدو غياب المصدر وكأنه انعدام للنشاط أو نجاح في الفحص.",
      radar_what_title: "ما يلزم قبل النشر",
      radar_gate_source: "للمصدر غرض موثق وشروط وحدود وصول ومسؤول تشغيلي معروف.",
      radar_gate_quality: "الجمع حديث ومكتمل بما يكفي لنطاقه المعلن واجتاز التحقق.",
      radar_gate_review: "وافق مراجع بشري على اللقطة وتأكد من عدم كشف معلومات خاصة.",
      radar_gate_trace: "كل قيمة مرتبطة بوقت ومنهج وسجل مصدر.",
      radar_contact: "استفسر عن تجربة قياس"
    },
    report: {
      page_label: "التقارير العامة",
      page_title: "لم تصدر أي نسخة عامة بعد.",
      page_lede: "لا ينبغي نشر تقرير إلا عندما يمكن فهم نطاقه ومصادره ومنهجه ومراجعته وحدوده بصورة مستقلة. ولا توجد في هذا المستودع نسخة عامة متحقق منها.",
      report_state: "لم يصدر تقرير",
      report_copy: "ستربط هذه الصفحة بالنسخ المؤرخة وسجل تصحيحها بعد اجتياز التقرير بوابة النشر. وحتى ذلك الحين لن تعرض أرقاماً مؤقتة أو نتائج محاكاة.",
      report_method: "اقرأ مبادئ القياس"
    },
    verify: {
      page_label: "تجربة أصحاب الحقوق",
      page_title: "نبني آلية المراجعة معاً.",
      page_lede: "لم تُطلق بوابة المراجعة الخاصة بعد. وتسعى وايب إلى جمع ملاحظات منظمة من أصحاب المحتوى حول جودة الأدلة وسياق الحقوق والتصحيح والحدود اللازمة لتجربة موثوقة.",
      verify_state: "مناقشة تجربة · لا توجد بوابة خاصة",
      verify_copy: "لا ترسل أعمالاً سرية أو ملفات جمهور أو بيانات دخول أو معلومات إنفاذ عبر هذا الموقع العام أو بريد عادي. يجب الاتفاق أولاً على قناة استلام آمنة ومعتمدة قبل مشاركة أي مادة حساسة.",
      verify_steps_title: "ما الذي تحدده التجربة المسؤولة",
      verify_step_scope: "صاحب حق واحد ونطاق عمل وإقليم واضحان ومستخدمون مفوضون بأسمائهم.",
      verify_step_sources: "مصادر عامة معتمدة ومراجعة للشروط والخصوصية والاحتفاظ ومسؤول عن الأعطال.",
      verify_step_review: "آلية لفحص كل سجل وتصحيحه أو الاعتراض عليه قبل أي إجراء.",
      verify_step_exit: "إجراء موثق للإيقاف والحذف والحوادث وتسليم العمل.",
      verify_contact: "ناقش تجربة دون مشاركة بيانات سرية"
    },
    governance: {
      page_label: "الخصوصية والحوكمة",
      page_title: "ظهور البيانات للعموم لا يمنح إذناً بجمعها.",
      page_lede: "يعتمد الموقف القانوني والخصوصي على المصدر والبيانات والغرض والاختصاص القضائي وطريقة النشر. توضح هذه الصفحة الضوابط التي يجب على وايب وضعها؛ وهي ليست مشورة قانونية أو شهادة امتثال.",
      governance_site_title: "هذا الموقع",
      governance_site_copy: "هذا الموقع الثابت لا يوفر تسجيل دخول أو استقبال ملفات أو موجز جمع مباشر. ويحفظ اختيار اللغة في المتصفح كي يتذكر الموقع العربية أو الإنجليزية. ولا يتضمن هذا التنفيذ تحليلات أو خدمة خطوط خارجية.",
      governance_sources_title: "قبل استخدام أي مصدر",
      governance_sources_copy: "تجب مراجعة شروط المصدر وتوجيهات robots وضوابط الوصول ومعدل الطلبات والبيانات الشخصية الظاهرة والغرض والاحتفاظ والقانون المحلي المنطبق. ويجب تسجيل القرار والمراجع والتاريخ. ووجود رابط عام لا يثبت الإذن.",
      governance_evidence_title: "قبل مشاركة أي نتيجة",
      governance_evidence_copy: "يجب تقليل البيانات وفصل الرصد العام عن سجلات صاحب الحق وتقييد الوصول حسب الدور وحفظ سجل التصحيح وتجنب نشر ما قد يكشف هوية شخص أو عملية رصد خاصة.",
      governance_law_title: "المراجعة المحلية ضرورية",
      governance_law_copy: "قبل الجمع أو استخدام الأدلة في أي سوق، يجب على مستشار قانوني محلي مؤهل مراجعة القواعد المنطبقة للخصوصية وحقوق النشر والأدلة والنقل عبر الحدود والوسطاء. ولا يحدد الموقع قانونية الإجراء أو يضمن قبول الأدلة.",
      governance_contact: "استفسر عن حوكمة التجربة"
    }
  }
};

const page = document.body.dataset.page || "home";
const languageButton = document.querySelector("[data-language-toggle]");
const stageDetail = document.querySelector("[data-stage-detail]");
const stages = document.querySelectorAll("[data-stage]");
let language = "en";

function applyLanguage(nextLanguage) {
  language = nextLanguage;
  const dictionary = translations[language];
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  document.title = dictionary.titles[page] || dictionary.titles.home;
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const value = dictionary[page]?.[element.dataset.i18n] ??
      dictionary.home[element.dataset.i18n];
    if (typeof value === "string") element.textContent = value;
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    const value = dictionary[page]?.[element.dataset.i18nAria] ??
      dictionary.home[element.dataset.i18nAria];
    if (typeof value === "string") element.setAttribute("aria-label", value);
  });
  if (languageButton) {
    languageButton.textContent = dictionary.home.language_button;
    languageButton.setAttribute("aria-label", dictionary.home.language_label);
  }
  updateStageDetail();
}

function updateStageDetail() {
  if (!stageDetail) return;
  const selected = document.querySelector("[data-stage][aria-pressed='true']");
  const key = selected?.dataset.detail;
  const detail = key && translations[language].home[key];
  if (typeof detail === "string") stageDetail.textContent = detail;
  const frame = stageDetail.closest(".signal-frame");
  if (frame && selected?.dataset.stageName) {
    frame.dataset.activeStage = selected.dataset.stageName;
  }
}

if (languageButton) {
  try {
    const stored = localStorage.getItem("wipe-language");
    if (stored === "en" || stored === "ar") language = stored;
  } catch {
    language = "en";
  }
  languageButton.addEventListener("click", () => {
    const nextLanguage = language === "en" ? "ar" : "en";
    applyLanguage(nextLanguage);
    try {
      localStorage.setItem("wipe-language", nextLanguage);
    } catch {
      // The language switch remains usable when storage is disabled.
    }
  });
}
applyLanguage(language);

stages.forEach((stage) => {
  stage.addEventListener("click", () => {
    stages.forEach((item) => item.setAttribute("aria-pressed", String(item === stage)));
    updateStageDetail();
  });
});

const signalFrame = document.querySelector(".signal-frame");
if (signalFrame && "IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      signalFrame.classList.add("is-visible");
      observer.disconnect();
    }
  }, { threshold: 0.18 });
  observer.observe(signalFrame);
} else if (signalFrame) {
  signalFrame.classList.add("is-visible");
}
