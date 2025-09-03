-- jobs table
CREATE TABLE jobs (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  company VARCHAR(255) NOT NULL,
  location VARCHAR(255),
  description TEXT,
  salary VARCHAR(100),
  posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- resumes table
CREATE TABLE resumes (
  id SERIAL PRIMARY KEY,
  filename VARCHAR(255) NOT NULL,
  emails TEXT,
  phones TEXT,
  skills TEXT,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
SELECT *
FROM jobs;
INSERT INTO jobs (title, company, location, description, salary)
VALUES (
    'Frontend Developer',
    'Google',
    'Remote',
    'Build UI for web apps',
    '$5000'
  ),
  (
    'Backend Developer',
    'Microsoft',
    'Bangalore',
    'Build APIs',
    '$6000'
  );