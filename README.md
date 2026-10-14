# HRH — กำลังคนด้านสุขภาพรายจังหวัดของไทย (research tree)

การวิเคราะห์สถานการณ์กำลังคน 4 วิชาชีพ พ.ศ. 2556–2568 (บทที่ 4) และแบบจำลองจัดสรรแพทย์รายจังหวัด 15 ปี พ.ศ. 2569–2583 (บทที่ 5) พร้อมโมดูลบริการที่พร้อมรับข้อมูล (ผู้สูงอายุ ไตวาย มะเร็ง)

**เริ่มที่ [PROJECT_LOG.md](PROJECT_LOG.md)** ซึ่งรวมสถานะล่าสุด ประวัติงาน คำสั่งที่ใช้ กับดักที่เคยเจอ และโจทย์ถัดไป ทุกครั้งที่ทำงานเสร็จ ให้บันทึกต่อในไฟล์นั้น

## โครงสร้าง

| โฟลเดอร์ | เนื้อหา |
|---|---|
| `config/` | config การวิเคราะห์ (`analysis.toml`, `source_registry.toml`, `chapter5.toml`, `validation.toml`, `chapter5_health_gain.toml`) และแพ็กเกจบริการ |
| `data/` | ข้อมูลนำเข้า (path ลงทะเบียนใน `source_registry.toml`), `data/map/` แผนที่และตารางเทียบรหัส, `data/processed/` cache (สร้างใหม่ได้) |
| `src/` | โค้ดวิเคราะห์: `chapter4/`, `chapter5/`, `services/`, `workspace/` |
| `notebooks/` | notebook ที่รันแล้ว: บทที่ 4 (4.1–4.6) และบทที่ 5 (5.1–5.3) |
| `outputs/` | ตาราง รูป claims และแผน (สร้างใหม่ได้ด้วย make) |
| `reports/` | รายงานฉบับสมบูรณ์ภาษาไทย (`chapter4_complete_th`, `chapter5_complete_th`), แม่แบบใน `templates/`, ต้นฉบับผู้เขียนใน `source/` |
| `docs/` | `decisions.md`, `methods_and_limitations.md`, `data.md`, `roadmap.md`, `service_modules.md`, `final_check.md` |
| `scripts/` | `acquisition/` (ดึงข้อมูลดิบ), `sync_scientific_source.py`, `data_readiness_inventory.py` |
| `tests/` | tests ของ `src/` |
| `workspaces/` | repo แยก (git-ignored): `HRH-authoring` (เว็บและ Workforce Lab, private) และ `HRH-model` (เว็บสาธารณะ) |

**ของที่อยู่นอก repo** (`../HRH_offrepo/`, รายการไฟล์ใน `MANIFEST.csv`)
- ข้อมูลดิบที่ดึงจากเว็บ
- archive รอบ ก.ย. 2569
- เว็บรุ่นเก่า (dashboard `web/`, `site/`, สำเนา `story/`) และเอกสารของเว็บรุ่นนั้น

## คำสั่งหลัก

```bash
make help                 # รายการคำสั่ง
make chapter4             # บทที่ 4 ทั้งหมด (~3 นาทีเมื่อใช้ cache)
make chapter5             # บทที่ 5 ทั้งหมด (~70 นาที; ควรรันแบบ detach ดู PROJECT_LOG.md)
make chapter4-report      # render รายงานใหม่จาก claims (วินาที)
make chapter5-report
make test                 # tests
make sync-lab-source      # ส่งโค้ดวิทยาศาสตร์ไป workspaces/HRH-authoring
```

ใช้ Python ใน `.venv/` การแก้ `src/chapter4/*.py`, `config/analysis.toml`, `config/source_registry.toml` หรือ `config/chapter5.toml` ทำให้ต้องคำนวณแผนบทที่ 5 ใหม่ทั้งหมด

## สัญญาอนุญาต

ดู `LICENSE.text`
