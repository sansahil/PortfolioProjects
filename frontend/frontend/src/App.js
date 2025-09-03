import React, { useEffect, useState } from "react";

function JobList() {
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    fetch("http://localhost:5000/api/jobs")  // backend URL
      .then(res => res.json())
      .then(data => setJobs(data.jobs))
      .catch(err => console.error("Error fetching jobs:", err));
  }, []);

  return (
    <div>
      <h2>Available Jobs</h2>
      <ul>
        {jobs.map(job => (
          <li key={job.id}>
            {job.title} - {job.company} ({job.location})
          </li>
        ))}
      </ul>
    </div>
  );
}

export default JobList;
