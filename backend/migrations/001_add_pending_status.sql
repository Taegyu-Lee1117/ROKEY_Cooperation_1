BEGIN;

ALTER TABLE order_history
    DROP CONSTRAINT IF EXISTS order_history_status_check;

ALTER TABLE order_history
    ALTER COLUMN status SET DEFAULT 'PENDING';

ALTER TABLE order_history
    ADD CONSTRAINT order_history_status_check
    CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'));

COMMIT;
