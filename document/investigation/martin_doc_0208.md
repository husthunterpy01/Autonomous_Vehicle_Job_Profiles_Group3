# 1. Autoware structure document
 Based on the given autoware document, the categories for the job profiles within this domain can temporarily be divided into 9 sub categories, each of them will contain some keywords that's unique to them, which can help user to identify which job roles have been mentioned. The list of the categories with the keywords can be recorded as followed:

 | Category | Keywords |
|---|---|
| **Sensing** | camera_driver, lidar_driver, radar_driver, gnss_driver, imu_driver, point cloud / pointcloud, velodyne, distortion correction, ring_outlier_filter, sensor calibration |
| **Localization** | ndt_scan_matcher, ekf_localizer, gyro_odometer, NDT (Normal Distributions Transform), pose estimation, dead reckoning, twist estimator, SLAM |
| **Perception** | object_recognition, object detection, object tracking, multi_object_tracker, euclidean_cluster, roi_cluster_fusion, camera-lidar fusion, sensor fusion, semantic segmentation, traffic light recognition / classifier, TensorRT, YOLOX, computer vision |
| **Planning** | mission_planner, behavior_path_planner, motion_velocity_planner, lane change, lane following, obstacle avoidance, path smoother / path optimizer, scenario selector, freespace planner, motion planning, trajectory generation |
| **Control** | trajectory_follower, lateral controller, longitudinal controller, MPC (model predictive control), PID control, vehicle_cmd_gate |
| **System** | diagnostics, emergency_handler, fail-safe, system monitor, safety monitoring, autoware_state |
| **Vehicle Interface** | vehicle_interface, raw_vehicle_cmd_converter, drive-by-wire, CAN bus, pacmod |
| **Map** | lanelet2, HD map, vector map, pointcloud map, map projection |
| **Cross-cutting (any category)** | ROS 2, rclcpp, autonomous driving, autonomous vehicle, self-driving |

**Notes on use:**
- Multi-word phrases (e.g. "object tracking") are stronger signals than single generic words (e.g. "tracking").
- Use this list as a first-pass filter and as hints for an LLM classifier — job postings phrase things more loosely than ROS package names.
- "ROS 2" / "rclcpp" / "autonomous driving" are strong AV-relevance signals but not category-specific; use them for an initial "is this an AV job" filter, not for category assignment.

# 2. Company profile scraping strategy

Based on some researchs, we categorize the company list into some categories based on the scraping capability approach

### Published API
Job vacancies are published through a third-party Applicant Tracking System such as Greenhouse, Lever, or SmartRecruiters.
### HTML / JavaScript / Selenium Scraping
Jobs are available through a public careers page, but no stable documented public API was confirmed.
### Anti-Bot or Proprietary Portal
The recruitment site uses a custom portal, heavy JavaScript, regional routing, CAPTCHA, or other access restrictions.
### No Stable Source Confirmed
No reliable company-hosted job listing, API, or structured careers page was confirmed.
k

| Company | Current job source / ATS | Anti-bot risk | Confidence | Direct API endpoint / Career page |
|---|---|---|---|---|
| 42dot | Custom first-party careers site | Low | High | https://www.42dot.ai/ko/careers/open-roles |
| ADASTEC | No structured job board confirmed | Low | Low | https://www.adastec.com/ |
| Aurora | Custom careers frontend, with Greenhouse-style job identifiers | Low–Medium | Medium | https://aurora.tech/careers |
| AutoBrains | Company careers/culture pages; structured openings not confirmed | Low | Low | https://autobrains.ai/life-at-autobrains/ |
| Apollo / Baidu | Proprietary Baidu recruitment portal | High | Medium | No stable public URL confirmed |
| Applied Intuition | **Ashby** | Low | High | `https://api.ashbyhq.com/posting-api/job-board/applied` |
| AImotive | Standalone current job board not confirmed; may recruit through parent-company channels | Low–Medium | Low | No standalone careers page confirmed |
| Avride | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/avride/jobs` |
| Bot.Auto | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/botauto/jobs` |
| Bosch | **SmartRecruiters** | Low | High | `https://api.smartrecruiters.com/v1/companies/BoschGroup/postings` |
| DeepRoute | Custom company site; stable ATS not confirmed | Medium | Low | Needs direct inspection |
| DiDi | Mixed: proprietary global portal plus **Greenhouse for DiDi Labs** | Medium | High | `https://boards-api.greenhouse.io/v1/boards/didi/jobs` |
| May Mobility | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/maymobility/jobs` |
| Gatik | First-party careers page; current public ATS not confirmed | Low–Medium | Medium | https://archive.gatik.ai/careers/ |
| Inceptio.ai | Stable company-hosted vacancy feed not confirmed | Low–Medium | Low | No stable feed confirmed |
| Horizon Robotics | Proprietary or regional recruitment source | Medium–High | Low | Needs direct inspection |
| Huawei | Proprietary Huawei recruitment portal | High | High | https://career.huawei.com/ |
| Kodiak | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/kodiak/jobs` |
| Einride | Public careers source; ATS not confidently identified | Low–Medium | Low | Careers page exists; ATS unconfirmed |
| Latitude AI | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/latitude/jobs` |
| GM | Dynamic first-party corporate job portal, associated with enterprise ATS workflows | Medium | High | https://search-careers.gm.com/en/ |
| Mobileye | Public careers source, but ATS/API not confirmed | Medium | Low | https://www.mobileye.com/about/ |
| Motional | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/motional/jobs` |
| Momenta | Regional/custom recruitment channels | Medium–High | Low | Needs direct inspection |
| Nuro | Current ATS not confidently reverified | Medium | Low | Needs re-verification |
| NVIDIA | Enterprise dynamic recruitment portal using Workday-related infrastructure | Medium | High | https://www.nvidia.com/en-au/about-nvidia/careers/ |
| Pony.ai | Proprietary first-party careers portal | Medium–High | High | https://careers.pony.ai/ |
| Plus AI | Stable ATS/API not currently confirmed | Medium | Low | https://www.plus.ai/ |
| QCraft | Stable public job board not confirmed | Medium | Low | No stable board confirmed |
| Stack AV | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/stackav/jobs` |
| Tensor / AutoX | Custom first-party careers page with job IDs | Low | High | https://www.tensor.auto/careers |
| Torc Robotics | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/torcrobotics/jobs` |
| Tier IV | First-party careers site; public ATS API not confirmed | Low–Medium | Low | Needs direct inspection |
| Waabi | **Lever** | Low | High | `https://api.lever.co/v0/postings/waabi?mode=json` |
| Waymo | Custom dedicated careers platform | Medium | High | https://careers.withwaymo.com/ |
| Wayve | **Greenhouse** | Low | Medium–High | `https://boards-api.greenhouse.io/v1/boards/wayve/jobs` |
| WeRide | Current ATS/API not confidently confirmed | Medium | Low | Needs direct inspection |
| Woven by Toyota | Custom first-party careers platform with structured job-detail URLs | Low–Medium | High | https://woven.toyota/en/careers |
| Vay | **Greenhouse** | Low | High | `https://boards-api.greenhouse.io/v1/boards/vay/jobs` |
| XPeng | First-party Join Us page | Medium | High | https://www.xpeng.com/au/join-us |
| Zoox | Custom dynamic careers page | Medium | High | https://zoox.com/careers |



