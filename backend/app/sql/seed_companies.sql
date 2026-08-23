-- Reseed companies, locations, and job postings on every server start (local/testing).
TRUNCATE TABLE company CASCADE;

INSERT INTO company (company_id, name, website_url, career_page_url, company_type, datasource_status) VALUES
  ('11111111-1111-1111-1111-111111111001', '42dot', 'https://www.42dot.ai', 'https://www.42dot.ai/ko/careers/open-roles', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111002', 'ADASTEC', 'https://www.adastec.com', 'https://www.adastec.com/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111003', 'Aurora', 'https://aurora.tech', 'https://aurora.tech/careers', 'AV_Startup', 'provisional'),
  ('11111111-1111-1111-1111-111111111004', 'AutoBrains', 'https://autobrains.ai', 'https://autobrains.ai/life-at-autobrains/', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111005', 'Apollo / Baidu', 'https://www.apollo.auto', 'https://www.apollo.auto/careers', 'OEM_Tech', 'provisional'),
  ('11111111-1111-1111-1111-111111111006', 'Applied Intuition', 'https://www.appliedintuition.com', 'https://api.ashbyhq.com/posting-api/job-board/applied', 'AV_Tools', 'confirmed'),
  ('11111111-1111-1111-1111-111111111007', 'AImotive', 'https://aimotive.com', 'https://aimotive.com/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111008', 'Avride', 'https://www.avride.ai', 'https://boards-api.greenhouse.io/v1/boards/avride/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111009', 'Bot.Auto', 'https://www.bot.auto', 'https://boards-api.greenhouse.io/v1/boards/botauto/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111010', 'Bosch', 'https://www.bosch.com', 'https://api.smartrecruiters.com/v1/companies/BoschGroup/postings', 'Supplier', 'confirmed'),
  ('11111111-1111-1111-1111-111111111011', 'DeepRoute', 'https://www.deeproute.ai', 'https://www.deeproute.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111012', 'DiDi', 'https://www.didiglobal.com', 'https://boards-api.greenhouse.io/v1/boards/didi/jobs', 'OEM_Tech', 'confirmed'),
  ('11111111-1111-1111-1111-111111111013', 'May Mobility', 'https://maymobility.com', 'https://boards-api.greenhouse.io/v1/boards/maymobility/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111014', 'Gatik', 'https://gatik.ai', 'https://archive.gatik.ai/careers/', 'AV_Startup', 'provisional'),
  ('11111111-1111-1111-1111-111111111015', 'Inceptio.ai', 'https://www.inceptio.ai', 'https://www.inceptio.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111016', 'Horizon Robotics', 'https://en.horizon.cc', 'https://en.horizon.cc/careers', 'AV_Chip', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111017', 'Huawei', 'https://www.huawei.com', 'https://career.huawei.com/', 'OEM_Tech', 'confirmed'),
  ('11111111-1111-1111-1111-111111111018', 'Kodiak', 'https://kodiak.ai', 'https://boards-api.greenhouse.io/v1/boards/kodiak/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111019', 'Einride', 'https://www.einride.tech', 'https://www.einride.tech/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111020', 'Latitude AI', 'https://lat.ai', 'https://boards-api.greenhouse.io/v1/boards/latitude/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111021', 'GM', 'https://www.gm.com', 'https://search-careers.gm.com/en/', 'OEM', 'confirmed'),
  ('11111111-1111-1111-1111-111111111022', 'Mobileye', 'https://www.mobileye.com', 'https://www.mobileye.com/about/', 'AV_Chip', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111023', 'Motional', 'https://motional.com', 'https://boards-api.greenhouse.io/v1/boards/motional/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111024', 'Momenta', 'https://www.momenta.ai', 'https://www.momenta.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111025', 'Nuro', 'https://www.nuro.ai', 'https://www.nuro.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111026', 'NVIDIA', 'https://www.nvidia.com', 'https://www.nvidia.com/en-au/about-nvidia/careers/', 'AV_Chip', 'confirmed'),
  ('11111111-1111-1111-1111-111111111027', 'Pony.ai', 'https://www.pony.ai', 'https://careers.pony.ai/', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111028', 'Plus AI', 'https://www.plus.ai', 'https://www.plus.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111029', 'QCraft', 'https://www.qcraft.ai', 'https://www.qcraft.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111030', 'Stack AV', 'https://stackav.com', 'https://boards-api.greenhouse.io/v1/boards/stackav/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111031', 'Tensor / AutoX', 'https://www.tensor.auto', 'https://www.tensor.auto/careers', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111032', 'Torc Robotics', 'https://torc.ai', 'https://boards-api.greenhouse.io/v1/boards/torcrobotics/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111033', 'Tier IV', 'https://tier4.jp', 'https://tier4.jp/en/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111034', 'Waabi', 'https://waabi.ai', 'https://api.lever.co/v0/postings/waabi?mode=json', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111035', 'Waymo', 'https://waymo.com', 'https://careers.withwaymo.com/', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111036', 'Wayve', 'https://wayve.ai', 'https://boards-api.greenhouse.io/v1/boards/wayve/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111037', 'WeRide', 'https://www.weride.ai', 'https://www.weride.ai/careers', 'AV_Startup', 'unconfirmed'),
  ('11111111-1111-1111-1111-111111111038', 'Woven by Toyota', 'https://woven.toyota', 'https://woven.toyota/en/careers', 'OEM_Tech', 'confirmed'),
  ('11111111-1111-1111-1111-111111111039', 'Vay', 'https://vay.io', 'https://boards-api.greenhouse.io/v1/boards/vay/jobs', 'AV_Startup', 'confirmed'),
  ('11111111-1111-1111-1111-111111111040', 'XPeng', 'https://www.xpeng.com', 'https://www.xpeng.com/au/join-us', 'OEM', 'confirmed'),
  ('11111111-1111-1111-1111-111111111041', 'Zoox', 'https://zoox.com', 'https://zoox.com/careers', 'AV_Startup', 'confirmed');

-- Company locations (linked to seeded companies above).
INSERT INTO company_location (location_id, country, city, is_hq, company_id) VALUES
  ('22222222-2222-2222-2222-222222222001', 'United States', 'Mountain View', TRUE,  '11111111-1111-1111-1111-111111111035'), -- Waymo HQ
  ('22222222-2222-2222-2222-222222222002', 'United States', 'San Francisco', FALSE, '11111111-1111-1111-1111-111111111035'), -- Waymo
  ('22222222-2222-2222-2222-222222222003', 'Canada',        'Toronto',       TRUE,  '11111111-1111-1111-1111-111111111034'), -- Waabi HQ
  ('22222222-2222-2222-2222-222222222004', 'United States', 'San Francisco', FALSE, '11111111-1111-1111-1111-111111111034'), -- Waabi
  ('22222222-2222-2222-2222-222222222005', 'Germany',       'Stuttgart',     TRUE,  '11111111-1111-1111-1111-111111111010'), -- Bosch HQ
  ('22222222-2222-2222-2222-222222222006', 'United States', 'Sunnyvale',     FALSE, '11111111-1111-1111-1111-111111111010'), -- Bosch
  ('22222222-2222-2222-2222-222222222007', 'United States', 'Pittsburgh',    TRUE,  '11111111-1111-1111-1111-111111111030'), -- Stack AV HQ
  ('22222222-2222-2222-2222-222222222008', 'United States', 'Pittsburgh',    TRUE,  '11111111-1111-1111-1111-111111111003'), -- Aurora HQ
  ('22222222-2222-2222-2222-222222222009', 'United States', 'Mountain View', FALSE, '11111111-1111-1111-1111-111111111003'), -- Aurora
  ('22222222-2222-2222-2222-222222222010', 'United States', 'Santa Clara',   TRUE,  '11111111-1111-1111-1111-111111111026'), -- NVIDIA HQ
  ('22222222-2222-2222-2222-222222222011', 'United States', 'Foster City',   TRUE,  '11111111-1111-1111-1111-111111111041'), -- Zoox HQ
  ('22222222-2222-2222-2222-222222222012', 'United States', 'Boston',        TRUE,  '11111111-1111-1111-1111-111111111023'), -- Motional HQ
  ('22222222-2222-2222-2222-222222222013', 'United States', 'Ann Arbor',     TRUE,  '11111111-1111-1111-1111-111111111013'), -- May Mobility HQ
  ('22222222-2222-2222-2222-222222222014', 'United Kingdom','London',        TRUE,  '11111111-1111-1111-1111-111111111036'), -- Wayve HQ
  ('22222222-2222-2222-2222-222222222015', 'United States', 'Austin',        TRUE,  '11111111-1111-1111-1111-111111111032'), -- Torc HQ
  ('22222222-2222-2222-2222-222222222016', 'United States', 'Mountain View', TRUE,  '11111111-1111-1111-1111-111111111006'), -- Applied Intuition HQ
  ('22222222-2222-2222-2222-222222222017', 'South Korea',   'Seoul',         TRUE,  '11111111-1111-1111-1111-111111111001'), -- 42dot HQ
  ('22222222-2222-2222-2222-222222222018', 'Turkey',        'Istanbul',      TRUE,  '11111111-1111-1111-1111-111111111002'), -- ADASTEC HQ
  ('22222222-2222-2222-2222-222222222019', 'Israel',        'Tel Aviv',      TRUE,  '11111111-1111-1111-1111-111111111004'), -- AutoBrains HQ
  ('22222222-2222-2222-2222-222222222020', 'China',         'Beijing',       TRUE,  '11111111-1111-1111-1111-111111111005'), -- Apollo / Baidu HQ
  ('22222222-2222-2222-2222-222222222021', 'Hungary',       'Budapest',      TRUE,  '11111111-1111-1111-1111-111111111007'), -- AImotive HQ
  ('22222222-2222-2222-2222-222222222022', 'United States', 'Austin',        TRUE,  '11111111-1111-1111-1111-111111111008'), -- Avride HQ
  ('22222222-2222-2222-2222-222222222023', 'United States', 'San Francisco', TRUE,  '11111111-1111-1111-1111-111111111009'), -- Bot.Auto HQ
  ('22222222-2222-2222-2222-222222222024', 'China',         'Shenzhen',      TRUE,  '11111111-1111-1111-1111-111111111011'), -- DeepRoute HQ
  ('22222222-2222-2222-2222-222222222025', 'China',         'Beijing',       TRUE,  '11111111-1111-1111-1111-111111111012'), -- DiDi HQ
  ('22222222-2222-2222-2222-222222222026', 'United States', 'Mountain View', TRUE,  '11111111-1111-1111-1111-111111111014'), -- Gatik HQ
  ('22222222-2222-2222-2222-222222222027', 'China',         'Shanghai',      TRUE,  '11111111-1111-1111-1111-111111111015'), -- Inceptio.ai HQ
  ('22222222-2222-2222-2222-222222222028', 'China',         'Beijing',       TRUE,  '11111111-1111-1111-1111-111111111016'), -- Horizon Robotics HQ
  ('22222222-2222-2222-2222-222222222029', 'China',         'Shenzhen',      TRUE,  '11111111-1111-1111-1111-111111111017'), -- Huawei HQ
  ('22222222-2222-2222-2222-222222222030', 'United States', 'Mountain View', TRUE,  '11111111-1111-1111-1111-111111111018'), -- Kodiak HQ
  ('22222222-2222-2222-2222-222222222031', 'Sweden',        'Gothenburg',    TRUE,  '11111111-1111-1111-1111-111111111019'), -- Einride HQ
  ('22222222-2222-2222-2222-222222222032', 'United States', 'Pittsburgh',    TRUE,  '11111111-1111-1111-1111-111111111020'), -- Latitude AI HQ
  ('22222222-2222-2222-2222-222222222033', 'United States', 'Detroit',       TRUE,  '11111111-1111-1111-1111-111111111021'), -- GM HQ
  ('22222222-2222-2222-2222-222222222034', 'Israel',        'Jerusalem',     TRUE,  '11111111-1111-1111-1111-111111111022'), -- Mobileye HQ
  ('22222222-2222-2222-2222-222222222035', 'China',         'Suzhou',        TRUE,  '11111111-1111-1111-1111-111111111024'), -- Momenta HQ
  ('22222222-2222-2222-2222-222222222036', 'United States', 'Mountain View', TRUE,  '11111111-1111-1111-1111-111111111025'), -- Nuro HQ
  ('22222222-2222-2222-2222-222222222037', 'United States', 'Fremont',       TRUE,  '11111111-1111-1111-1111-111111111027'), -- Pony.ai HQ
  ('22222222-2222-2222-2222-222222222038', 'United States', 'Santa Clara',   TRUE,  '11111111-1111-1111-1111-111111111028'), -- Plus AI HQ
  ('22222222-2222-2222-2222-222222222039', 'United States', 'San Jose',      TRUE,  '11111111-1111-1111-1111-111111111029'), -- QCraft HQ
  ('22222222-2222-2222-2222-222222222040', 'China',         'Shenzhen',      TRUE,  '11111111-1111-1111-1111-111111111031'), -- Tensor / AutoX HQ
  ('22222222-2222-2222-2222-222222222041', 'Japan',         'Nagoya',        TRUE,  '11111111-1111-1111-1111-111111111033'), -- Tier IV HQ
  ('22222222-2222-2222-2222-222222222042', 'China',         'Guangzhou',     TRUE,  '11111111-1111-1111-1111-111111111037'), -- WeRide HQ
  ('22222222-2222-2222-2222-222222222043', 'Japan',         'Tokyo',         TRUE,  '11111111-1111-1111-1111-111111111038'), -- Woven by Toyota HQ
  ('22222222-2222-2222-2222-222222222044', 'Germany',       'Berlin',        TRUE,  '11111111-1111-1111-1111-111111111039'), -- Vay HQ
  ('22222222-2222-2222-2222-222222222045', 'China',         'Guangzhou',     TRUE,  '11111111-1111-1111-1111-111111111040'); -- XPeng HQ

-- Job postings
-- employment_type: 1=FULL_TIME, 2=PART_TIME, 3=CONTRACT, 5=INTERN
-- seniority_level: 1=JUNIOR, 2=MID, 3=SENIOR, 4=PRINCIPAL, 5=LEAD, 6=MANAGER
INSERT INTO jobposting (job_id, name, title, department, employment_type, job_location, seniority_level, salary_average, salary_currency, raw_description, posted_date, source_platform, extraction_confidence, company_id) VALUES
  ('33333333-3333-3333-3333-333333333001', 'waymo-software-engineer-perception-mv', 'Software Engineer, Perception', 'Perception', 1, 'Mountain View, CA, USA', 3, 185000, 'USD', 'Build and ship perception models for Waymo Driver. Work on LiDAR/camera fusion, tracking, and on-vehicle inference.', '2026-08-01 09:00:00', 'Greenhouse', 0.92, '11111111-1111-1111-1111-111111111035'),
  ('33333333-3333-3333-3333-333333333002', 'waymo-ml-engineer-behavior-sf', 'Machine Learning Engineer, Behavior', 'Behavior', 1, 'San Francisco, CA, USA', 4, 220000, 'USD', 'Design ML systems for trajectory prediction and decision making in complex urban environments.', '2026-08-05 14:30:00', 'Greenhouse', 0.90, '11111111-1111-1111-1111-111111111035'),
  ('33333333-3333-3333-3333-333333333003', 'waabi-research-scientist-simulation-toronto', 'Research Scientist, Simulation', 'Research', 1, 'Toronto, ON, Canada', 3, 160000, 'CAD', 'Advance differentiable simulation and closed-loop evaluation for autonomous trucking.', '2026-07-28 11:00:00', 'Lever', 0.88, '11111111-1111-1111-1111-111111111034'),
  ('33333333-3333-3333-3333-333333333004', 'waabi-software-engineer-infrastructure-sf', 'Software Engineer, Infrastructure', 'Infrastructure', 1, 'San Francisco, CA, USA', 2, 175000, 'USD', 'Build scalable training and evaluation pipelines for autonomy research workloads.', '2026-08-10 16:00:00', 'Lever', 0.87, '11111111-1111-1111-1111-111111111034'),
  ('33333333-3333-3333-3333-333333333005', 'bosch-embedded-software-engineer-sunnyvale', 'Embedded Software Engineer, ADAS', 'ADAS', 1, 'Sunnyvale, CA, USA', 2, 145000, 'USD', 'Develop safety-critical embedded software for driver-assistance ECUs.', '2026-07-15 08:00:00', 'SmartRecruiters', 0.85, '11111111-1111-1111-1111-111111111010'),
  ('33333333-3333-3333-3333-333333333006', 'stackav-systems-engineer-pittsburgh', 'Systems Engineer, Autonomy', 'Systems', 1, 'Pittsburgh, PA, USA', 3, 155000, 'USD', 'Own cross-stack integration for Stack AV autonomous trucking systems.', '2026-08-08 10:15:00', 'Greenhouse', 0.91, '11111111-1111-1111-1111-111111111030'),
  ('33333333-3333-3333-3333-333333333007', 'aurora-motion-planning-engineer-pittsburgh', 'Motion Planning Engineer', 'Planning', 1, 'Pittsburgh, PA, USA', 3, 170000, 'USD', 'Implement and validate motion planning algorithms for highway and urban trucking routes.', '2026-08-03 13:45:00', 'Greenhouse', 0.89, '11111111-1111-1111-1111-111111111003'),
  ('33333333-3333-3333-3333-333333333008', 'nvidia-autonomous-vehicle-intern-santaclara', 'Autonomous Vehicle Software Intern', 'AV Software', 5, 'Santa Clara, CA, USA', 1, 55, 'USD', 'Internship supporting NVIDIA DRIVE software stacks, simulation tooling, and AV demos. Hourly rate.', '2026-08-12 09:30:00', 'NVIDIA Careers', 0.80, '11111111-1111-1111-1111-111111111026'),
  ('33333333-3333-3333-3333-333333333009', 'zoox-robotics-software-engineer-fostercity', 'Robotics Software Engineer', 'Robotics', 1, 'Foster City, CA, USA', 5, 195000, 'USD', 'Lead development of robotics software for Zoox purpose-built robotaxi platforms.', '2026-07-22 12:00:00', 'Zoox Careers', 0.93, '11111111-1111-1111-1111-111111111041'),
  ('33333333-3333-3333-3333-333333333010', 'motional-safety-engineer-boston', 'Functional Safety Engineer', 'Safety', 1, 'Boston, MA, USA', 3, 150000, 'USD', 'Drive ISO 26262 compliance and hazard analysis for Motional AV software and hardware.', '2026-08-06 15:20:00', 'Greenhouse', 0.86, '11111111-1111-1111-1111-111111111023'),
  ('33333333-3333-3333-3333-333333333011', 'wayve-applied-scientist-london', 'Applied Scientist, End-to-End Driving', 'Research', 1, 'London, United Kingdom', 3, 110000, 'GBP', 'Train and evaluate large-scale end-to-end driving models on diverse real-world fleets.', '2026-08-09 10:00:00', 'Greenhouse', 0.90, '11111111-1111-1111-1111-111111111036'),
  ('33333333-3333-3333-3333-333333333012', 'applied-intuition-simulation-engineer-mv', 'Simulation Engineer', 'Simulation', 1, 'Mountain View, CA, USA', 2, 165000, 'USD', 'Build high-fidelity simulation scenarios and tooling for AV validation customers.', '2026-08-11 17:00:00', 'Ashby', 0.84, '11111111-1111-1111-1111-111111111006');
