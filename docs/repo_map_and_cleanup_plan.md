# แผนที่ repo และข้อเสนอการจัดระเบียบ (14 ต.ค. 2569)

สถานะ: **ข้อเสนอเท่านั้น ยังไม่มีการลบหรือย้ายไฟล์ใด** ทุกข้อต้องรอเจ้าของโครงการอนุมัติ

เขียนจากมุมคนที่เพิ่งเข้ามาเห็น repo ครั้งแรก หลักฐานแต่ละแถวมาจากการค้นว่าโค้ด config Makefile และ tests ยังอ้างถึงโฟลเดอร์นั้นหรือไม่

## ปัญหาหลักที่คนใหม่จะเจอ

1. **งานปัจจุบันเกือบทั้งหมดยังไม่อยู่ใน git**
   - commit ล่าสุดของ repo นี้คือ 17 ส.ค. 2569
   - `src/`, `config/`, `docs/`, `notebooks/`, `outputs/`, `reports/`, `tests/` ยังเป็น untracked ทั้งหมด
   - ถ้าลบหรือย้ายผิด จะกู้คืนจาก git ไม่ได้ **ต้อง commit สภาพปัจจุบันก่อนจัดระเบียบ** (ข้อ 0 ด้านล่าง)
2. **มีเว็บ 3 รุ่นซ้อนกันใน root** และรุ่นที่ใช้จริงอยู่ที่อื่นแล้ว
   - รุ่น 1 (ก.ค.–ส.ค.): แดชบอร์ด Leaflet ใน `web/`
   - รุ่น 2 (6–7 ก.ย.): interactive report ใน `site/` และ `scripts/webexport/`
   - รุ่น 3 (26–27 ก.ย.): story site ใน `story/` และ `scripts/webstory/`
   - ตั้งแต่ 27 ก.ย. รุ่น 3 ย้ายไปอยู่ที่ `workspaces/HRH-authoring` (repo แยก) แล้ว สำเนาใน root จึงค้างอยู่ที่สภาพวันที่ 27 ก.ย.
3. **`output/` กับ `outputs/` ชื่อคล้ายกันแต่คนละยุค**
   - `outputs/` คือผลของ pipeline ปัจจุบัน
   - `output/` คือผลของสคริปต์รุ่นแรก ปนกับข้อมูลดิบที่ดึงจากเว็บ (`output/scraped`, 1.9 GB) และไฟล์แผนที่ที่ pipeline ปัจจุบันยังใช้ (`output/map/geo_prov.geojson`)
4. **เอกสารสถานะหลายรุ่นอยู่ปนกัน** ได้แก่ `ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`, `QA_REPORT.md`, `SOURCE_INVENTORY.md`, `UPDATE_GUIDE.md` ใน root ซึ่งพูดถึงเว็บรุ่น 2 ทั้งหมด และ `docs/completion_report.md` (26 ก.ย.) กับ `docs/chapter5_completion_report.md` (27 ก.ย.) ซึ่งตัวเลขบางส่วนล้าสมัยแล้ว
5. **Makefile มี target ที่ใช้ไม่ได้แล้ว**
   - `make analysis` เรียกสคริปต์ 8 ตัวที่ไม่มีอยู่จริง
   - `web-*` และ `story-*` ทำงานกับสำเนาเก่าใน root

## สถานะแต่ละส่วน

| ส่วน | บทบาท | ยังใช้อยู่? (หลักฐาน) | ข้อเสนอ |
|---|---|---|---|
| `src/chapter4`, `src/chapter5`, `src/services`, `src/workspace` | โค้ดวิเคราะห์หลัก (ต้นฉบับ) | ใช่ | **เก็บ** |
| `config/*.toml`, `config/services`, `config/workspace` | config การวิเคราะห์ | ใช่ | **เก็บ** |
| `config/web/` | config ของเว็บรุ่น 3 | ไม่ (ตัวจริงอยู่ใน authoring และต่างจากนี้แล้ว) | archive |
| `data/` (ยกเว้น `processed`, `cold_data`) | ข้อมูลนำเข้าดิบ | ใช่ (`source_registry.toml`) | **เก็บ** |
| `data/processed/` | cache ที่สร้างใหม่ได้ | ใช่ | เก็บ (สร้างใหม่ได้) |
| `data/cold_data/` | ข้อมูลดิบที่ไม่ได้ใช้ ถูกกันไว้ตั้งแต่ ก.ย. | ไม่ | เก็บไว้เป็นสำรอง หรือย้ายออกนอก repo |
| `notebooks/chapter4_*`, `chapter5_*` | notebook ที่รันแล้วของบท 4–5 | ใช่ | **เก็บ** (notebook บท 5 ยังเป็นผลวันที่ 27 ก.ย. ต้องรัน `make chapter5-notebooks`) |
| `outputs/chapter4_1..4_6`, `chapter5`, `shared`, `services`, `workspaces` | ผลปัจจุบัน | ใช่ | **เก็บ** (สร้างใหม่ได้ทั้งหมด) |
| `outputs/web/` (82 MB) | release ของเว็บรุ่น 3 ฉบับ root (ก.ย.) | ไม่ | ลบ (สร้างใหม่ได้ ตัวจริงอยู่ใน authoring) |
| `outputs/chapter5_scenarios/` | ผล scenario | ว่าง | ลบโฟลเดอร์ว่าง |
| `reports/` | รายงานภาษาไทยฉบับสมบูรณ์, `templates/`, `source/` (ต้นฉบับของผู้เขียน) | ใช่ | **เก็บ** |
| `docs/` (ไฟล์ปัจจุบัน) | วิธีการ การตัดสินใจ แผน ความคืบหน้า คำขอข้อมูล | ใช่ | **เก็บ** และจัดเป็นโฟลเดอร์ย่อย (ดูโครงสร้างใหม่) |
| `docs/completion_report.md`, `docs/chapter5_completion_report.md`, `docs/file_migration_manifest.csv`, `docs/reconciliation_log.csv` | บันทึกประวัติรอบ ก.ย. | อ้างอิงได้ แต่ตัวเลขบางส่วนล้าสมัย | ย้ายไป `docs/history/` |
| `docs/web_story/` (102 MB), `docs/web-brief/` | เอกสารเว็บรุ่น 3 และ 2 | ไม่ (authoring มีของตัวเอง) | archive |
| `tests/` | ชุดทดสอบ | บางไฟล์ทดสอบเว็บรุ่น 2–3 ใน root (`test_web_bundle.py` ล้มเพราะขาดไฟล์เก่า) | เก็บเฉพาะที่ทดสอบ `src/` และ archive ไฟล์ทดสอบเว็บเก่า |
| `scripts/scrp_hrh.py`, `scrp_spc.py`, `scrp_serv.py`, `process.py`, `pivot_epi.py`, `scrp_epi.ipynb` | ดึงและทำความสะอาดข้อมูลจากเว็บ (ที่มาของ `data/`) | ใช้เมื่อดึงข้อมูลใหม่ | **เก็บ** ย้ายไป `scripts/acquisition/` |
| `scripts/sync_scientific_source.py`, `data_readiness_inventory.py` | เครื่องมือปัจจุบัน | ใช่ | **เก็บ** |
| `scripts/export_for_external_analysis.py` | ส่งออกข้อมูลให้นักวิเคราะห์ภายนอก (25 ก.ย.) | ไม่มีใครเรียก | ถามเจ้าของ แล้วเก็บหรือ archive |
| `scripts/analyse.py`, `add_hrh_cadre.py`, `build_dashboard_data.py` | ตัวช่วยของ notebook รุ่นแรกและแดชบอร์ด `web/` | ไม่ | archive |
| `scripts/webexport/`, `make_site_atlas.py`, `site/`, `chapter4_outputs/` (โฟลเดอร์ว่าง) | เว็บรุ่น 2 | ไม่ (เหลือแค่ Makefile `web-*` และ tests เก่า) | archive |
| `story/`, `scripts/webstory/`, `requirements/story*.txt`, `dist/story-public/` | เว็บรุ่น 3 สำเนาใน root | ไม่ (ตัวจริงอยู่ใน `workspaces/HRH-authoring`) | archive |
| `web/`, `.github/workflows/pages.yml` | แดชบอร์ดรุ่น 1 ที่ deploy ขึ้น GitHub Pages เมื่อ push `main` | track อยู่ใน git และอาจยังมีคนเปิดอยู่ | **ถามเจ้าของ**: ถ้าลบแล้ว push หน้า Pages ของ repo นี้จะหายไปด้วย |
| `hrh.ipynb` (11 MB), `model.ipynb`, `situation.ipynb`, `spc.ipynb` | notebook วิเคราะห์รุ่นแรกใน root | ไม่ (pipeline ปัจจุบันแทนที่แล้ว) | archive (สองไฟล์แรก track อยู่ใน git จึงกู้คืนได้) |
| `output/scraped/` (1.9 GB) | ข้อมูลดิบที่ดึงจากเว็บ (ที่มาของ `data/epi` และอื่น ๆ) | ใช้เมื่อสร้าง `data/` ใหม่ | **ย้าย** ไป `data/raw_scraped/` (หรือเก็บนอก repo) |
| `output/map/` | ตารางเทียบรหัสที่ทำมือ และขอบเขตจังหวัด geojson | **ใช่**: `src/chapter5/pipeline.py:80`, `figures.py:352` | **ย้าย** ไป `data/map/` แล้วแก้ path สองจุดนี้ (เปลี่ยนเฉพาะโค้ดบท 5 จึงไม่ทำให้ต้องรันแผนใหม่) |
| `output/clean/`, `output/analyse/`, `output/model/`, `output/serv.csv`, `output/README_serv.md` | ผลกลางทางและผลวิเคราะห์ของรุ่นแรก | ไม่ | archive |
| `archive/` (457 MB, git-ignored) | ของที่ archive ไว้ตั้งแต่ ก.ย. | ไม่ | เก็บไว้ หรือย้ายออกไปไว้นอก repo |
| root `ARCHITECTURE.md`, `IMPLEMENTATION_STATUS.md`, `QA_REPORT.md`, `SOURCE_INVENTORY.md`, `UPDATE_GUIDE.md` | เอกสารของเว็บรุ่น 2 | ไม่ | ย้ายไป archive พร้อมเว็บรุ่น 2 |
| `README.md` (27 ก.ย.) | คำอธิบาย repo | ใช่ แต่ล้าสมัย (ยังไม่มี 4.5, 4.6, services, Phase 0) | **เขียนใหม่ให้สั้น** แล้วชี้ไปที่ `PROJECT_LOG.md` |
| `workspaces/HRH-authoring` | repo แยกของเว็บและ Lab (private) | ใช่ | เก็บ (git-ignored ใน root) |
| `workspaces/HRH-model` | repo แยกของเว็บสาธารณะ (GitHub `psitthirat/HRH-model`) | ใช่ | เก็บ |
| `.DS_Store`, `__pycache__`, `.pytest_cache` | ไฟล์ขยะของระบบ | ไม่ | ลบได้ทันที (ignore อยู่แล้ว) |

## โครงสร้างที่เสนอหลังจัดระเบียบ

```
HRH/
├── PROJECT_LOG.md        ← diary ของโครงการ อ่านเป็นไฟล์แรก
├── README.md             ← สั้น ๆ: โครงการคืออะไร อยู่ตรงไหน รันอย่างไร
├── Makefile              ← เหลือเฉพาะ chapter4*, chapter5*, services-population, sync-lab-*
├── config/               ← analysis, source_registry, chapter5, chapter5_health_gain, validation, services, workspace
├── data/                 ← ข้อมูลนำเข้า (+ map/ ที่ย้ายมาจาก output/map, raw_scraped/ ที่ย้ายมาจาก output/scraped)
├── src/                  ← chapter4, chapter5, services, workspace
├── notebooks/            ← chapter4_1..4_6, chapter5_1..5_3
├── outputs/              ← ผลทั้งหมด (สร้างใหม่ได้)
├── reports/              ← รายงานฉบับสมบูรณ์ + templates + source
├── docs/
│   ├── methods/          ← analytical_decisions, chapter5_methods, chapter5_decisions, methods_and_limitations, activity_fte_ledger, service_modules, spatial_anchoring_framework
│   ├── data/             ← data_catalog, data_requests, chapter5_data_requests, data_readiness_inventory
│   ├── plans/            ← next_phase_development_plan, next_phase_progress, phase0_reconciliation_map
│   ├── final_check/      ← log การตรวจ
│   └── history/          ← completion reports รอบ ก.ย., migration manifest, reconciliation log
├── scripts/              ← acquisition/ (scrapers, process, pivot_epi), sync_scientific_source.py, data_readiness_inventory.py
├── tests/                ← เฉพาะ tests ของ src/
└── workspaces/           ← HRH-authoring, HRH-model (repo แยก)
```

ถ้าย้ายโฟลเดอร์ใน `docs/` ต้องแก้ลิงก์ภายในเอกสารด้วย ผมจะทำส่วนนี้พร้อมกันและตรวจลิงก์เสียหลังย้าย

## ลำดับที่เสนอ (ทุกขั้นรอการอนุมัติ)

0. **Commit สภาพปัจจุบันของ root** หลังผ่าน final check: จะได้จุดย้อนกลับก่อนจัดระเบียบ
   - ไฟล์ใหญ่ตาม `.gitignore` (เช่น `output/scraped`, `archive`) ยังไม่ถูก commit
   - ควรเพิ่ม `outputs/` บางส่วนที่ใหญ่ (parquet, `outputs/web`) ใน `.gitignore` ก่อน
1. **Archive แทนการลบ:** ย้ายของในแถว "archive" ไปไว้ที่ `archive/2026-10-repo-cleanup/` พร้อม `MANIFEST.csv` (path เดิม, path ใหม่, SHA-256, เหตุผล) ย้อนกลับได้ทุกไฟล์
2. **ลบเฉพาะของที่สร้างใหม่ได้:** `outputs/web`, โฟลเดอร์ว่าง, `__pycache__`, `.DS_Store`
3. **ย้ายสองจุดที่ยังใช้งาน:** `output/map` ไป `data/map` (แก้ path ใน `src/chapter5` สองจุด แล้วรัน tests) และ `output/scraped` ไป `data/raw_scraped` (แก้ path ใน scrapers และ `pivot_epi.py`)
4. **ตัด Makefile:** ลบ `analysis`, `web-*`, `story-*` (ตัว story ใช้ใน authoring) แล้วรัน `make chapter4-test chapter5-test` และ pytest
5. **เขียน README ใหม่** ให้ชี้ไปที่ `PROJECT_LOG.md`
6. หลังจัดระเบียบ ทำ commit ที่สอง และบันทึกลง `PROJECT_LOG.md`

## สิ่งที่ต้องให้เจ้าของตัดสินใจ

1. Commit root ตอนนี้ได้หรือไม่ (ข้อ 0)
2. แดชบอร์ด `web/` บน GitHub Pages ยังต้องการให้เปิดอยู่หรือไม่
3. `archive/` และ `output/scraped` เก็บใน repo ต่อหรือย้ายไปไว้ที่ดิสก์อื่น
4. `scripts/export_for_external_analysis.py` ยังใช้อยู่หรือไม่
