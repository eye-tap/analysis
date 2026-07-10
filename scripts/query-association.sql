SELECT d.user_id as user_id, d.furhter_options as cohort, d.survey_id as surveyid
FROM (((annotator NATURAL JOIN app_user) users JOIN survey_users su ON su.users_id = users.user_id) u JOIN survey s
      ON u.survey_id = s.id) d
WHERE d.title <> 'testing'
  AND d.furhter_options <> '' AND survey_id <= 3;
