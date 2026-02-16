SELECT lbh.*, p.emp_id, p.full_name FROM ams_leavebalancehistory lbh JOIN profile p ON lbh.profile_id=p.id
WHERE lbh.date BETWEEN '2023-04-01' AND '2024-01-31' AND lbh.transaction = 'Leaves Earned'