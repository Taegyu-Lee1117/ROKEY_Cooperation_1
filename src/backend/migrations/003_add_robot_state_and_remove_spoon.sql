BEGIN;

ALTER TABLE error_log DROP CONSTRAINT IF EXISTS error_log_process_step_check;
ALTER TABLE error_log ADD CONSTRAINT error_log_process_step_check CHECK (
    process_step IN (
        'CUP_PICK', 'CUP_PLACE', 'SCOOP_PICK', 'MOVE_TO_ICECREAM',
        'SCOOP_ICECREAM', 'PUT_ICECREAM_IN_CUP', 'SCOOP_RETURN',
        'SERVE_CUP'
    )
);

ALTER TABLE error_log DROP CONSTRAINT IF EXISTS error_log_error_code_check;
ALTER TABLE error_log ADD CONSTRAINT error_log_error_code_check CHECK (
    error_code IN ('GRIP_FAILED', 'MOVE_FAILED', 'SCOOP_FAILED', 'UNKNOWN_ERROR')
);

CREATE TABLE IF NOT EXISTS robot_state (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    status VARCHAR(20) NOT NULL CHECK (
        status IN ('IDLE', 'READY', 'PROCESSING', 'RETURNING_HOME', 'ERROR', 'STOPPED')
    ),
    current_order_id INTEGER REFERENCES order_history(id),
    current_step VARCHAR(50) NOT NULL DEFAULT '',
    message VARCHAR(255) NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO robot_state (id, status, message)
VALUES (1, 'IDLE', '초기 상태')
ON CONFLICT (id) DO NOTHING;

COMMIT;
