-- Rebuild the questiontype enum so it matches helpers.enums.question_types.QuestionType.
-- Assumes the questions table is empty (so no data is lost when casting to TEXT).

BEGIN;

-- Detach the column from the existing enum.
ALTER TABLE questions
    ALTER COLUMN question_type
    TYPE TEXT USING question_type::TEXT;

-- Clean up any previous backup type name to avoid rename conflicts.
DROP TYPE IF EXISTS questiontype_old;

-- Rename the current type (if it exists) so we can recreate it cleanly.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'questiontype') THEN
        ALTER TYPE questiontype RENAME TO questiontype_old;
    END IF;
END
$$;

-- Recreate the enum with the correct values.
CREATE TYPE questiontype AS ENUM ('CONCENTRATION', 'SPEED', 'WORDS', 'SORTING', 'MULTITASKING');

-- Reattach the column to the recreated enum.
ALTER TABLE questions
    ALTER COLUMN question_type
    TYPE questiontype USING question_type::questiontype;

-- Drop the old enum definition.
DROP TYPE IF EXISTS questiontype_old;

COMMIT;
