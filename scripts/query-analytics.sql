SELECT d.user_id as user_id, d.analytics as analytics, d.survey_id as surveyid
FROM (((annotator NATURAL JOIN app_user) users JOIN survey_users su ON su.users_id = users.user_id) u JOIN survey s ON u.survey_id = s.id) d
WHERE d.analytics <> '' AND d.title <> 'testing' AND d.further_options <> '';
