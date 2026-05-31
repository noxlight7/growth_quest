from django.db import migrations


DROP_TRIGGERS_SQL = """
DROP TRIGGER IF EXISTS trg_characters_factions_same_adventure ON adventures_characterfaction;
DROP FUNCTION IF EXISTS enforce_character_faction_same_adventure();

DROP TRIGGER IF EXISTS trg_relationships_same_adventure ON adventures_characterrelationship;
DROP FUNCTION IF EXISTS enforce_relationship_same_adventure();
"""

CREATE_TRIGGERS_SQL = """
CREATE OR REPLACE FUNCTION enforce_character_faction_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    c_adv BIGINT;
    f_adv BIGINT;
BEGIN
    SELECT adventure_id INTO c_adv FROM adventures_character WHERE id = NEW.character_id;
    SELECT adventure_id INTO f_adv FROM adventures_faction WHERE id = NEW.faction_id;

    IF c_adv IS NULL OR f_adv IS NULL THEN
        RAISE EXCEPTION 'Character % or faction % not found', NEW.character_id, NEW.faction_id;
    END IF;

    IF c_adv <> f_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in character_factions: char %, faction %', c_adv, f_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_characters_factions_same_adventure
BEFORE INSERT OR UPDATE ON adventures_characterfaction
FOR EACH ROW EXECUTE FUNCTION enforce_character_faction_same_adventure();

CREATE OR REPLACE FUNCTION enforce_relationship_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    from_adv BIGINT;
    to_adv BIGINT;
BEGIN
    SELECT adventure_id INTO from_adv FROM adventures_character WHERE id = NEW.from_character_id;
    SELECT adventure_id INTO to_adv FROM adventures_character WHERE id = NEW.to_character_id;

    IF from_adv IS NULL OR to_adv IS NULL THEN
        RAISE EXCEPTION 'Relationship characters not found: % -> %',
            NEW.from_character_id, NEW.to_character_id;
    END IF;

    IF from_adv <> to_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in relationships: from %, to %', from_adv, to_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_relationships_same_adventure
BEFORE INSERT OR UPDATE ON adventures_characterrelationship
FOR EACH ROW EXECUTE FUNCTION enforce_relationship_same_adventure();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0022_remove_character_faction_relationship_adventure"),
    ]

    operations = [
        migrations.RunSQL(DROP_TRIGGERS_SQL + CREATE_TRIGGERS_SQL, reverse_sql=DROP_TRIGGERS_SQL),
    ]
