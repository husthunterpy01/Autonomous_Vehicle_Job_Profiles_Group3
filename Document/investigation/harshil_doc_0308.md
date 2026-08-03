# Requirement Verification and Domain Research

## 1. Purpose

This document verifies the current requirements for the Autonomous Vehicle Job Profiles project and extends the team’s domain research into a form that can guide implementation.

It connects the existing Autoware, Apollo, dataset, and scraping research to:

- a shared job-profile taxonomy;
- proposed classification rules;
- skill and technology normalisation rules;
- project requirements;
- recommended data fields;
- open questions for the team or client.

The aim is to reduce ambiguity before the team develops the scraping pipeline, classification process, backend search functions, and dashboard.

---

## 2. Existing Research Reviewed

The following project research has already been reviewed:

- Autoware role categories and platform-specific keywords.
- Apollo architecture, Cyber RT terminology, and Apollo-specific role vocabulary.
- Autonomous-driving datasets and benchmarks such as Waymo Open Dataset, nuScenes, Argoverse, KITTI, and BDD100K.
- Company career-page and applicant-tracking-system scraping strategies.
- The project problem statement, MVP deliverables, scope boundaries, and traceability requirements.

---

## 3. Unified Job-Profile Taxonomy

Different autonomous-driving platforms use different terminology for similar technical responsibilities.

The project should therefore use shared, normalised categories rather than creating separate category systems for every software platform.

| Normalised category | Autoware examples | Apollo examples | General job-advertisement terms |
|---|---|---|---|
| **Sensing** | `camera_driver`, `lidar_driver`, `radar_driver`, sensor calibration | Camera, LiDAR, and radar inputs | Sensor integration, calibration, data acquisition |
| **Localisation** | `ndt_scan_matcher`, `ekf_localizer`, SLAM | HD-map-relative localisation | Pose estimation, dead reckoning, localisation engineering |
| **Perception** | `object_recognition`, `multi_object_tracker`, sensor fusion | Obstacle detection, traffic-light detection, YOLO | Computer vision, object detection, semantic segmentation |
| **Prediction** | Often combined with planning | Lane Sequence Predictor, Inter-TNT, trajectory prediction | Behaviour prediction, motion forecasting |
| **Planning** | `behavior_path_planner`, `motion_velocity_planner` | EM Planner | Path planning, motion planning, trajectory generation |
| **Control** | `trajectory_follower`, `vehicle_cmd_gate` | Throttle, brake, steering, PID, MPC | Vehicle control, control systems |
| **Vehicle Interface** | CAN bus, drive-by-wire, `vehicle_interface` | CanBus and command interfaces | Embedded vehicle integration |
| **Mapping** | Lanelet2, HD map, point-cloud map | HD-map-related components | Mapping, map engineering, geospatial systems |
| **System and Safety** | Diagnostics, `emergency_handler`, fail-safe | Monitor, Guardian, HMI | Functional safety, diagnostics, system monitoring |

This taxonomy allows jobs that use different technical vocabularies to be grouped under the same higher-level category.

For example:

| Platform-specific term | Normalised category |
|---|---|
| `behavior_path_planner` | Planning |
| EM Planner | Planning |
| `multi_object_tracker` | Perception |
| Obstacle detection | Perception |
| `vehicle_cmd_gate` | Control |
| Throttle, brake, and steering control | Control |

---

## 4. Proposed Classification Rules

The keyword lists should be treated as classification signals rather than absolute rules.

A job advertisement may use general wording, platform-specific terms, or responsibilities that span multiple technical areas.

The proposed first-pass process is:

1. Confirm that the advertisement contains at least one autonomous-vehicle relevance signal.
2. Search the job title, responsibilities, requirements, and description for category-specific terms.
3. Give more importance to multi-word phrases and platform-specific terms than to broad single words.
4. Allow one advertisement to match more than one category when responsibilities overlap.
5. Preserve the original matched terms for traceability.
6. Mark uncertain or conflicting classifications for manual review or later LLM-assisted validation.

Possible autonomous-vehicle relevance signals include:

- Autoware
- ApolloAuto
- Apollo Cyber
- Cyber RT
- ROS 2
- `rclcpp`
- autonomous driving
- autonomous vehicle
- self-driving
- Waymo Open Dataset
- nuScenes
- Argoverse

### Example

A role containing:

> LiDAR sensor calibration and point-cloud object detection

may reasonably be classified under both:

- **Sensing**
- **Perception**

This is because sensor calibration relates to Sensing, while object detection relates to Perception.

---

## 5. Skill and Technology Normalisation

The same technical concept may appear with different spellings, abbreviations, or product names.

The project should maintain a normalisation dictionary while preserving the original wording from the advertisement.

| Original terms | Normalised term |
|---|---|
| ROS2, ROS 2 | ROS 2 |
| lidar, LiDAR, LIDAR | LiDAR |
| pointcloud, point cloud | Point Cloud |
| self-driving, autonomous driving, autonomous vehicle | Autonomous Driving |
| MPC, model predictive control | Model Predictive Control |
| NDT, Normal Distributions Transform | NDT |
| CyberRT, Cyber RT, Apollo Cyber | Cyber RT |
| Waymo dataset, Waymo Open Dataset | Waymo Open Dataset |

Normalisation will support:

- consistent search results;
- reliable filtering;
- accurate aggregate skill counts;
- comparison between companies;
- clearer dashboard visualisations.

The original advertisement wording should still be retained for traceability.

---

## 6. Datasets and Benchmarks as AV-Relevance Signals

Dataset and benchmark names are useful cross-cutting indicators because they are relatively specific to autonomous-driving, perception, prediction, and computer-vision work.

Examples include:

- Waymo Open Dataset
- nuScenes
- Argoverse
- Argoverse 2
- KITTI
- BDD100K

These names should generally be stored as technologies, datasets, or benchmark experience.

They can strengthen the decision that a posting is related to autonomous vehicles, but they should not automatically assign one exact job category.

For example:

- A role mentioning nuScenes may relate to Perception, Prediction, or Machine Learning.
- A role mentioning KITTI may relate to Computer Vision, Perception, or Benchmark Evaluation.
- A role mentioning Argoverse may relate to Prediction, Mapping, or Motion Forecasting.

---

## 7. Implications for Project Requirements

The existing domain research produces the following proposed requirements for the MVP:

- The system should recognise terminology from multiple autonomous-driving platforms, including Autoware and Apollo.
- Platform-specific terms should map to shared job-profile categories.
- A job advertisement may be associated with more than one category.
- Dataset and benchmark names should be stored as searchable technologies or skills.
- Original and normalised terminology should both be retained.
- Classification should include an uncertainty or confidence indicator where evidence is insufficient.
- Users should be able to search using general terms and known platform-specific terms.
- The source URL, collection date, and matched evidence should be retained for traceability.
- Missing or uncertain values should be recorded clearly rather than guessed.
- The classification approach should support later refinement using manual review, NLP, or LLM-based methods.

---

## 8. Recommended Data Fields for Classification

The following fields are recommended for the structured job dataset.

| Field | Purpose |
|---|---|
| `job_title_original` | Original title from the employer |
| `job_description_original` | Original advertisement text or permitted source reference |
| `company` | Normalised company name |
| `source_url` | Original posting URL |
| `collection_date` | Date the advertisement was collected |
| `matched_keywords` | Terms that triggered AV relevance or category assignment |
| `normalised_skills` | Standardised skills and technologies |
| `primary_category` | Main job-profile category, if selected |
| `secondary_categories` | Additional matching categories |
| `classification_confidence` | High, Medium, Low, or another agreed score |
| `review_status` | Automatic, manually reviewed, or uncertain |

These fields will support:

- search and filtering;
- classification testing;
- manual validation;
- aggregate analysis;
- traceability to the original source.

---

## 9. Questions Requiring Team or Client Confirmation

1. Should the dashboard display one primary category, multiple categories, or both?
2. Should Prediction remain a separate category or be grouped with Planning?
3. Should datasets and benchmarks appear as skills, technologies, or a separate filter?
4. What minimum evidence is required before a category is assigned?
5. Will uncertain classifications be manually reviewed during the MVP?
6. Should the first MVP use keyword rules only, or combine rules with an LLM classifier?
7. What confidence scale should be used, and how should each level be defined?
8. Should users be able to filter by both general category names and platform-specific terms?
9. Should classification evidence be visible in the dashboard or only stored internally?
10. How should jobs with no clear category be displayed?

---

## 10. Recommended Next Steps

- Agree on the unified category list before implementing classification.
- Create a shared keyword and synonym dictionary in a machine-readable format.
- Test the taxonomy against a small sample of real job advertisements.
- Record false positives, false negatives, and overlapping categories.
- Refine the rules before scaling collection across the full company list.
- Keep all source links and validation notes in the project documentation.
- Confirm unresolved requirements with the team or client.
- Review the taxonomy after the first batch of collected jobs.

---

## 11. Conclusion

The existing Autoware, Apollo, dataset, and scraping research provides a strong technical foundation for the project.

The next requirement is to convert platform-specific vocabulary into a consistent and traceable classification model.

A shared taxonomy, normalisation rules, multi-label support, and explicit handling of uncertainty will make the collected job data more useful for both:

- curriculum analysis; and
- job-market exploration.

This document should be treated as an initial proposal and refined after the team tests it against real autonomous-vehicle job advertisements.