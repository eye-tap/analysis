SELECT id AS session_id, reading_session_id
FROM annotation_session
WHERE annotation_session.survey_id <= 3
ORDER BY id;
