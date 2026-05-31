from django.db import migrations


TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION enforce_character_same_adventure_refs()
RETURNS TRIGGER AS $$
DECLARE
    r_adv BIGINT;
    l_adv BIGINT;
BEGIN
    IF NEW.race_id IS NOT NULL THEN
        SELECT adventure_id INTO r_adv FROM adventures_race WHERE id = NEW.race_id;
        IF r_adv IS NULL OR r_adv <> NEW.adventure_id THEN
            RAISE EXCEPTION 'Race % belongs to adventure %, but character adventure is %',
                NEW.race_id, r_adv, NEW.adventure_id;
        END IF;
    END IF;

    IF NEW.location_id IS NOT NULL THEN
        SELECT adventure_id INTO l_adv FROM adventures_location WHERE id = NEW.location_id;
        IF l_adv IS NULL OR l_adv <> NEW.adventure_id THEN
            RAISE EXCEPTION 'Location % belongs to adventure %, but character adventure is %',
                NEW.location_id, l_adv, NEW.adventure_id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_characters_same_adventure_refs
BEFORE INSERT OR UPDATE ON adventures_character
FOR EACH ROW EXECUTE FUNCTION enforce_character_same_adventure_refs();

CREATE OR REPLACE FUNCTION enforce_race_ability_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    race_adv BIGINT;
    ab_adv   BIGINT;
BEGIN
    SELECT adventure_id INTO race_adv FROM adventures_race WHERE id = NEW.race_id;
    SELECT adventure_id INTO ab_adv   FROM adventures_ability WHERE id = NEW.ability_id;

    IF race_adv IS NULL OR ab_adv IS NULL THEN
        RAISE EXCEPTION 'Race % or ability % not found', NEW.race_id, NEW.ability_id;
    END IF;

    IF NEW.adventure_id <> race_adv OR NEW.adventure_id <> ab_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in races_abilities: row adv %, race adv %, ability adv %',
            NEW.adventure_id, race_adv, ab_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_races_abilities_same_adventure
BEFORE INSERT OR UPDATE ON adventures_raceability
FOR EACH ROW EXECUTE FUNCTION enforce_race_ability_same_adventure();

CREATE OR REPLACE FUNCTION enforce_character_ability_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    c_adv BIGINT;
    a_adv BIGINT;
BEGIN
    SELECT adventure_id INTO c_adv FROM adventures_character WHERE id = NEW.character_id;
    SELECT adventure_id INTO a_adv FROM adventures_ability   WHERE id = NEW.ability_id;

    IF c_adv IS NULL OR a_adv IS NULL THEN
        RAISE EXCEPTION 'Character % or ability % not found', NEW.character_id, NEW.ability_id;
    END IF;

    IF NEW.adventure_id <> c_adv OR NEW.adventure_id <> a_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in characters_abilities: row adv %, char adv %, ability adv %',
            NEW.adventure_id, c_adv, a_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_characters_abilities_same_adventure
BEFORE INSERT OR UPDATE ON adventures_characterability
FOR EACH ROW EXECUTE FUNCTION enforce_character_ability_same_adventure();

CREATE OR REPLACE FUNCTION enforce_character_faction_same_adventure()
RETURNS TRIGGER AS $$
DECLARE
    c_adv BIGINT;
    f_adv BIGINT;
BEGIN
    SELECT adventure_id INTO c_adv FROM adventures_character WHERE id = NEW.character_id;
    SELECT adventure_id INTO f_adv FROM adventures_faction   WHERE id = NEW.faction_id;

    IF c_adv IS NULL OR f_adv IS NULL THEN
        RAISE EXCEPTION 'Character % or faction % not found', NEW.character_id, NEW.faction_id;
    END IF;

    IF NEW.adventure_id <> c_adv OR NEW.adventure_id <> f_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in characters_factions: row adv %, char adv %, faction adv %',
            NEW.adventure_id, c_adv, f_adv;
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
    to_adv   BIGINT;
BEGIN
    SELECT adventure_id INTO from_adv FROM adventures_character WHERE id = NEW.from_character_id;
    SELECT adventure_id INTO to_adv   FROM adventures_character WHERE id = NEW.to_character_id;

    IF from_adv IS NULL OR to_adv IS NULL THEN
        RAISE EXCEPTION 'Relationship characters not found: % -> %',
            NEW.from_character_id, NEW.to_character_id;
    END IF;

    IF NEW.adventure_id <> from_adv OR NEW.adventure_id <> to_adv THEN
        RAISE EXCEPTION 'Adventure mismatch in relationships: row adv %, from adv %, to adv %',
            NEW.adventure_id, from_adv, to_adv;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_relationships_same_adventure
BEFORE INSERT OR UPDATE ON adventures_characterrelationship
FOR EACH ROW EXECUTE FUNCTION enforce_relationship_same_adventure();
"""


REVERSE_SQL = """
DROP TRIGGER IF EXISTS trg_relationships_same_adventure ON adventures_characterrelationship;
DROP FUNCTION IF EXISTS enforce_relationship_same_adventure();

DROP TRIGGER IF EXISTS trg_characters_factions_same_adventure ON adventures_characterfaction;
DROP FUNCTION IF EXISTS enforce_character_faction_same_adventure();

DROP TRIGGER IF EXISTS trg_characters_abilities_same_adventure ON adventures_characterability;
DROP FUNCTION IF EXISTS enforce_character_ability_same_adventure();

DROP TRIGGER IF EXISTS trg_races_abilities_same_adventure ON adventures_raceability;
DROP FUNCTION IF EXISTS enforce_race_ability_same_adventure();

DROP TRIGGER IF EXISTS trg_characters_same_adventure_refs ON adventures_character;
DROP FUNCTION IF EXISTS enforce_character_same_adventure_refs();
"""


class Migration(migrations.Migration):
    dependencies = [
        ("adventures", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(TRIGGER_SQL, REVERSE_SQL),
    ]
