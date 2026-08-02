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

| Company | Current job source / ATS | Recommended scraping method | Anti-bot risk | Confidence |
|---|---|---|---|---|
| 42dot | Custom first-party careers site | Direct HTML or embedded JSON; inspect XHR; Selenium fallback | Low | High |
| ADASTEC | No structured job board confirmed | Check careers/contact pages manually; periodic HTML monitoring | Low | Low |
| Aurora | Custom careers frontend, with Greenhouse-style job identifiers | Inspect page XHR and Greenhouse integration first; Selenium fallback | Low–Medium | Medium |
| AutoBrains | Company careers/culture pages; structured openings not confirmed | Direct HTML first; manual monitoring if no vacancy feed appears | Low | Low |
| Apollo / Baidu | Proprietary Baidu recruitment portal | Inspect XHR; browser automation where required | High | Medium |
| Applied Intuition | **Ashby** | **Published Ashby Job Posting API** | Low | High |
| AImotive | Standalone current job board not confirmed; may recruit through parent-company channels | Search parent-company ATS; manual monitoring | Low–Medium | Low |
| Avride | **Greenhouse** | **Published Greenhouse Job Board API** | Low | High |
| Bot.Auto | **Greenhouse** | **Published Greenhouse Job Board API** | Low | High |
| Bosch | **SmartRecruiters** | **Published SmartRecruiters Posting API** | Low | High |
| DeepRoute | Custom company site; stable ATS not confirmed | Direct HTML/XHR investigation; Selenium fallback | Medium | Low |
| DiDi | Mixed: proprietary global portal plus **Greenhouse for DiDi Labs** | Greenhouse API for DiDi Labs; XHR/browser method for global vacancies | Medium | High |
| May Mobility | **Greenhouse** | **Published Greenhouse Job Board API** | Low | High |
| Gatik | First-party careers page; current public ATS not confirmed | Direct HTML and embedded JSON; inspect XHR; Selenium fallback | Low–Medium | Medium |
| Inceptio.ai | Stable company-hosted vacancy feed not confirmed | Manual monitoring; inspect company and regional recruiting channels | Low–Medium | Low |
| Horizon Robotics | Proprietary or regional recruitment source | Inspect network requests; browser automation if necessary | Medium–High | Low |
| Huawei | Proprietary Huawei recruitment portal | XHR investigation or Selenium/Playwright | High | High |
| Kodiak | **Greenhouse** | **Published Greenhouse Job Board API** | Low | High |
| Einride | Public careers source; ATS not confidently identified | Direct HTML/XHR first; Selenium fallback | Low–Medium | Low |
| Latitude AI | **Greenhouse** | **Published Greenhouse Job Board API** | Low | High |
| GM | Dynamic first-party corporate job portal, associated with enterprise ATS workflows | Inspect JSON/XHR endpoints; browser automation only when required | Medium | High |
| Mobileye | Public careers source, but ATS/API not confirmed | Inspect HTML and XHR; Selenium fallback | Medium | Low |
| Motional | **Greenhouse** | **Published Greenhouse Job Board API** | Low | High |
| Momenta | Regional/custom recruitment channels | Direct HTML/XHR investigation; browser automation or manual monitoring | Medium–High | Low |
| Nuro | Current ATS not confidently reverified | Inspect current careers links and network requests before