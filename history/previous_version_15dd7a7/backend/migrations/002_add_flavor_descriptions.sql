ALTER TABLE icecream_flavor
    ADD COLUMN IF NOT EXISTS name_en VARCHAR(50) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS description VARCHAR(120) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS description_en VARCHAR(120) NOT NULL DEFAULT '';

UPDATE icecream_flavor
SET name_en = CASE name
        WHEN '바닐라' THEN 'Vanilla'
        WHEN '초콜릿' THEN 'Chocolate'
        WHEN '딸기' THEN 'Strawberry'
        ELSE name_en
    END,
    description = CASE name
        WHEN '바닐라' THEN '부드럽고 진한 기본 바닐라'
        WHEN '초콜릿' THEN '초코칩이 씹히는 진한 초콜릿'
        WHEN '딸기' THEN '생딸기 과육이 들어간 상큼함'
        ELSE description
    END,
    description_en = CASE name
        WHEN '바닐라' THEN 'Smooth and rich classic vanilla'
        WHEN '초콜릿' THEN 'Rich chocolate with crunchy chips'
        WHEN '딸기' THEN 'Fresh and fruity strawberry'
        ELSE description_en
    END
WHERE name_en = '' OR description = '' OR description_en = '';

INSERT INTO icecream_flavor (name, name_en, description, description_en, is_available)
VALUES ('민트초코', 'Mint Chocolate', '상쾌한 민트와 초콜릿 칩', 'Refreshing mint with chocolate chips', FALSE),
       ('쿠키앤크림', 'Cookies and Cream', '바삭한 쿠키가 가득한 크림', 'Creamy ice cream packed with cookies', FALSE)
ON CONFLICT (name) DO NOTHING;

-- 최초 키오스크 메뉴는 바닐라, 초콜릿, 딸기 세 가지로 고정한다.
UPDATE icecream_flavor
SET is_available = name IN ('바닐라', '초콜릿', '딸기');
