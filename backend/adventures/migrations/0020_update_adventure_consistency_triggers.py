from django.db import migrations


DROP_TRIGGERS_SQL = """
DROP TRIGGER IF EXISTS trg_character_techniques_same_adventure ON adventures_charactertechnique;
DROP FUNCTION IF EXISTS enforce_character_technique_same_adventure();

DROP TRIGGER IF EXISTS trg_character_systems_same_adventure ON adventures_charactersystem;
DROP FUNCTION IF EXISTS enforce_character_system_same_adventure();

DROP TRIGGER IF EXISTS trg_techniques_same_adventure_system ON adventures_technique;
DROP FUNCTION IF EXISTS enforce_technique_same_adventure_as_system();
"""

CREATE_TRIGGERS_SQL = """
CREATE OR REPLACE FUNCTION enforce_character_system_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    c_adv BIGINT;
    s_adv BIGINT;
BEGIN
    SELECT adventure_id INTO c_adv FROM adventures_character WHERE id = NEW.character_id;
    SELECT adventure_id INTO s_adv FROM adventures_skillsystem WHERE id = NEW.system_id;

    IF c_adv IS NULL OR s_adv IS NULL THEN
        RAISE EXCEPTION 'Character % or system % not found', NEW.character_id, NEW.system_id;
    END IF;

    IF c_adv <> s_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in character_systems: char %, system %', c_adv, s_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_character_systems_same_adventure
BEFORE INSERT OR UPDATE ON adventures_charactersystem
FOR EACH ROW EXECUTE FUNCTION enforce_character_system_same_adventure();

CREATE OR REPLACE FUNCTION enforce_character_technique_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    c_adv BIGINT;
    t_adv BIGINT;
BEGIN
    SELECT adventure_id INTO c_adv FROM adventures_character WHERE id = NEW.character_id;
    SELECT s.adventure_id INTO t_adv
    FROM adventures_technique t
    JOIN adventures_skillsystem s ON s.id = t.system_id
    WHERE t.id = NEW.technique_id;

    IF c_adv IS NULL OR t_adv IS NULL THEN
        RAISE EXCEPTION 'Character % or technique % not found', NEW.character_id, NEW.technique_id;
    END IF;

    IF c_adv <> t_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in character_techniques: char %, tech %', c_adv, t_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_character_techniques_same_adventure
BEFORE INSERT OR UPDATE ON adventures_charactertechnique
FOR EACH ROW EXECUTE FUNCTION enforce_character_technique_same_adventure();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0019_remove_character_system_technique_adventure"),
    ]

    operations = [
        migrations.RunSQL(DROP_TRIGGERS_SQL + CREATE_TRIGGERS_SQL, reverse_sql=DROP_TRIGGERS_SQL),
    ]
