"""Fictional demo data: one job and four CVs. All people, companies and contact details are invented."""

JOB = {
    "title": "Python Backend Developer",
    "department": "Engineering",
    "location": "London (hybrid)",
    "description": (
        "We are looking for a backend developer to build and run the APIs behind our recruitment "
        "products. You will design REST services in Python, model data in PostgreSQL, and deploy "
        "containerised services to the cloud. You will work in a small agile team and mentor juniors."
    ),
    "criteria": [
        {"key": "python", "label": "Python in production (3+ years)", "weight": 3, "must_have": True},
        {"key": "api", "label": "REST API development with FastAPI, Django or Flask", "weight": 2, "must_have": True},
        {"key": "sql", "label": "PostgreSQL / SQL data modelling", "weight": 2, "must_have": False},
        {"key": "cloud", "label": "Docker and cloud deployment (AWS, Azure or GCP)", "weight": 1.5, "must_have": False},
        {"key": "mentoring", "label": "Mentoring or technical leadership", "weight": 1, "must_have": False},
    ],
}

CVS = {
    "amara_okafor.pdf": """Amara Okafor
Senior Backend Engineer | amara.okafor@example.com | +44 7700 900101 | Manchester

PROFILE
Backend engineer with seven years building Python services for fintech and logistics.

EXPERIENCE
Senior Backend Engineer, LedgerLoop Ltd, 2021 - Present
- Designed REST APIs in FastAPI serving 2M requests/day.
- Modelled PostgreSQL schemas and tuned SQL queries, cutting report time by 60%.
- Deployed services with Docker on AWS ECS; introduced Terraform.
- Mentoring two junior developers; led the API guild.

Backend Developer, ParcelPath, 2018 - 2021
- Built Django REST services in Python for route optimisation.
- Maintained PostgreSQL databases and Redis caches.

EDUCATION
BSc Computer Science, University of Leeds, 2018

SKILLS
Python, FastAPI, Django, PostgreSQL, SQL, Redis, Docker, AWS, Terraform, Git, Agile
CERTIFICATIONS
AWS Certified Developer - Associate
""",
    "liam_chen.pdf": """Liam Chen
Full-Stack Developer | liam.chen@example.com | +44 7700 900202 | London

PROFILE
Full-stack developer focused on React front-ends with some Python back-end work.

EXPERIENCE
Full-Stack Developer, BrightCart, 2022 - Present
- Built React and TypeScript storefront features.
- Wrote small Flask endpoints in Python for internal tools.
- Used MySQL and basic SQL reporting.

Junior Web Developer, Pixel & Co, 2020 - 2022
- JavaScript and Node.js websites for agency clients.

EDUCATION
BA Digital Media, University of Brighton, 2020

SKILLS
JavaScript, TypeScript, React, Node.js, Python, Flask, MySQL, Git
""",
    "sofia_marquez.pdf": """Sofia Marquez
Data Engineer | sofia.marquez@example.com | +44 7700 900303 | Bristol

PROFILE
Data engineer with strong SQL and Python skills, moving towards API development.

EXPERIENCE
Data Engineer, Northwind Analytics, 2020 - Present
- Built Python ETL pipelines loading data into PostgreSQL and BigQuery.
- Designed SQL data models for analytics; wrote complex SQL.
- Containerised jobs with Docker and scheduled them on GCP.
- Built an internal FastAPI service exposing data quality metrics.

Analyst, CityData, 2018 - 2020
- SQL reporting and Python automation.

EDUCATION
MSc Data Science, University of Bristol, 2018

SKILLS
Python, SQL, PostgreSQL, FastAPI, Docker, GCP, Airflow, Git
""",
    "kwame_mensah.pdf": """Kwame Mensah
Java Developer | kwame.mensah@example.com | +44 7700 900404 | Birmingham

PROFILE
Java developer with a background in enterprise systems, learning Python in my spare time.

EXPERIENCE
Java Developer, Midland Insurance, 2019 - Present
- Spring Boot microservices and REST APIs in Java.
- Oracle and SQL stored procedures.
- Scrum team member; coached new joiners on code reviews.

EDUCATION
HND Computing, Birmingham Metropolitan College, 2019

SKILLS
Java, Spring Boot, SQL, Oracle, Jenkins, Git, Scrum
""",
}
