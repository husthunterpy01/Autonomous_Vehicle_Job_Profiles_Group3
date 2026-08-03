# 3. Open-source AV stack survey — Apollo

Autoware isn't the only stack out there. Baidu's Apollo is the other major open-source one, and a couple of
companies on our list are either Apollo itself or Baidu-linked (Apollo/Baidu, DiDi), so we'll probably run into job
posts using Apollo's own terms instead of the usual Autoware/ROS wording.

## Architecture

Apollo has four core modules, tied together by **Cyber RT** — its own pub/sub middleware, basically Apollo's answer
to ROS 2:

| Module | What it does | Notable sub-components |
|---|---|---|
| **Perception** | Detects what's around the vehicle | Obstacle detection, traffic light detection, camera-lidar-radar fusion, YOLO-based object detection, HD-map-relative localization |
| **Prediction** | Forecasts where detected obstacles are headed | Container / Scenario / Evaluator / Predictor sub-modules; Free Move Predictor, Single Lane Predictor, Lane Sequence Predictor, semantic-map pedestrian prediction, Inter-TNT model |
| **Planning** | Plans the trajectory | EM Planner |
| **Control** | Executes the trajectory | Throttle / brake / steering commands, PID / MPC control |

One thing worth flagging: Apollo is only partially open-source. The perception/prediction/planning/control code is
public, but HD maps and cloud services stay closed. Autoware is fully open under community governance. That's a
real difference between the two, and might explain different hiring patterns around map/cloud roles at
Apollo-based companies vs. Autoware-based ones.

## Extra keywords (Apollo vocabulary)

| Category | Apollo-specific keywords |
|---|---|
| Perception | perception, obstacle detection, traffic light detection, YOLO, camera-lidar-radar fusion |
| Prediction | prediction, trajectory prediction, Lane Sequence Predictor, Inter-TNT, Free Move Predictor |
| Planning | planning, EM planner |
| Control | control, throttle/brake/steering, PID control, MPC |
| Cross-cutting (any category) | Cyber RT, Apollo Cyber, ApolloAuto |

Note: Prediction gets its own row here to match the architecture section above — Apollo treats it as a distinct
module, and Adrian's kickoff-meeting description of a typical AV org also called out a separate "prediction team"
from planning/control. Worth flagging that Martin's Autoware category list doesn't currently have a standalone
Prediction bucket either, so the same addition probably needs to happen there too before this becomes the shared
taxonomy DOC-3 builds the ERD from.

Source: [Open-Source Autonomous Driving Software Platforms: Comparison of Autoware and Apollo (arXiv 2501.18942)](https://arxiv.org/abs/2501.18942),
[Apollo prediction module docs](https://github.com/ApolloAuto/apollo/blob/master/modules/prediction/README.md),
[Apollo 3.0 Software Architecture](https://daobook.github.io/apollo/docs/specs/Apollo_3.0_Software_Architecture.html).

# 4. Open dataset survey

Open datasets give a much more intuitive feel for the tech than an architecture diagram does, and dataset/benchmark
names showing up in a job posting are a pretty strong signal on their own that it's an AV-relevant role.

| Dataset | Scale | Sensor coverage | Geography | Notes |
|---|---|---|---|---|
| **Waymo Open Dataset** | 7.65M unique tracks (motion), 104k training segments | Camera + LiDAR; rich label set (boxes, human keypoints, panoptic segmentation) | Multiple US cities | Strong, well-synchronized sensor data; widely used as a perception/prediction benchmark |
| **nuScenes** | 1,000 scenes (20s each, 12Hz), ~4.3k tracks | Camera + LiDAR + radar | Boston + Singapore | Smaller than Waymo/Argoverse but an early, widely-cited benchmark; known ~5–10ms sensor sync gap |
| **Argoverse / Argoverse 2** | 11.7M unique tracks, 324k training segments | 7 ring cameras (360°) + LiDAR | Six US cities | Largest track count of the three; strong sync quality; 360° camera coverage stands out |

## Why it's useful for classification

These datasets aren't just raw driving footage — each one is built around a specific set of benchmark tasks/
challenges, and it turns out those task names are exactly the kind of language that shows up in job postings.
Went through Waymo's and nuScenes' own pages to check what tasks they actually define:

- **Waymo Open Dataset** (three datasets in one): Perception → 2D/3D object detection, tracking, semantic
  segmentation. Motion → motion forecasting, interaction prediction, behavior modeling. End-to-End → end-to-end
  driving, multimodal reasoning, long-tail/rare scenario evaluation.
- **nuScenes**: object detection (3D bounding boxes), tracking, prediction (trajectory forecasting), semantic
  segmentation (lidarseg), panoptic segmentation.

A JD saying "3D object detection" or "motion forecasting" is more likely to show up than one literally naming a
dataset — so these task terms are the stronger, more direct classification signal, and map straight onto our
existing categories:

| Category | Task keywords (from Waymo / nuScenes) |
|---|---|
| Perception | 2D/3D object detection, multi-object tracking, semantic segmentation, panoptic segmentation |
| Prediction | motion forecasting, trajectory prediction, interaction prediction, behavior modeling |
| Cross-cutting (any category) | end-to-end driving, multimodal reasoning, long-tail scenario evaluation |

The dataset *names* themselves (Waymo Open Dataset, nuScenes, Argoverse, Argoverse 2, KITTI, BDD100K) are still
worth keeping as a secondary signal — mainly useful as a general "this is AV-relevant" flag on the rarer occasions
a posting name-drops one directly, rather than for deciding which category it belongs to:

| Category | Keywords |
|---|---|
| **Datasets & Benchmarks** (cross-cutting, secondary AV-relevance signal) | Waymo Open Dataset, nuScenes, Argoverse, Argoverse 2, KITTI, BDD100K |

Sources:
- [Open-Source Autonomous Driving Software Platforms: Comparison of Autoware and Apollo](https://arxiv.org/abs/2501.18942)
- [A Performance Evaluation of Open Source Autonomous Driving Frameworks (IEEE)](https://ieeexplore.ieee.org/document/10918696/)
- [15 Best Open-Source Autonomous Driving Datasets](https://medium.com/analytics-vidhya/15-best-open-source-autonomous-driving-datasets-34324676c8d7)
- [A Survey on Autonomous Driving Datasets: Statistics, Annotation Quality, and a Future Outlook (arXiv 2401.01454)](https://arxiv.org/html/2401.01454v2)

# 5. Architecture diagrams & intro videos

Everything in the tables above was derived secondhand from these sources, so linking the originals here for
traceability, and so anyone on the team can go straight to the primary material instead of trusting our summaries.

## Autoware

The actual diagram is here: [Autoware architecture overview (SVG)](https://tier4.github.io/autoware-documentation/tier4-main/design/autoware-architecture/image/autoware-architecture-overview.drawio.svg)
— it lays out the six stacks (sensing, mapping, localization, perception, planning, control) and how they connect,
basically the visual version of the category list. For the write-up around it, the
[Autoware Design docs](https://autowarefoundation.github.io/autoware-documentation/main/design/) are the starting
point. There's also a node-level diagram one step deeper (the actual node graph for a default setup), but that one
can lag behind the latest release — `rqt_graph` would be the live source of truth if we ever run Autoware
ourselves.

(Note: the main docs site got restructured recently and a couple of the deep-links there 404 now, so the diagram
above is pulled from TIER IV's mirror of the docs instead, which is confirmed working.)

For a video, [Simon Thompson's talk from TIER IV](https://www.youtube.com/watch?v=HorirfS-Euc) at the Autoware
Tutorial (IEEE IV 2025) is the one to watch. It's an actual technical walkthrough rather than a marketing reel, so
it explains the reasoning behind the architecture, not just what it looks like.

## Apollo

The diagram: [Apollo 3.0 software architecture (PNG)](https://daobook.github.io/apollo/_images/Apollo_3.0_SW.png)
— shows how Perception, Prediction, Localization, Routing, Planning, Control, CanBus, HMI, Monitor, and Guardian
all talk to each other over pub/sub topics. It's from the same doc used in section 3, [How to Understand Apollo's
Architecture and Workflow](https://daobook.github.io/apollo/docs/howto/how_to_understand_architecture_and_workflow.html).
Heads up: that doc is no longer on Apollo's current `master` branch (looks like it got removed/moved at some
point), so linking a mirrored copy that's confirmed working instead of the dead GitHub path.

Video-wise, I couldn't track down one single explainer as clean as Autoware's, so I am linking the
[official Baidu Apollo YouTube channel](https://www.youtube.com/c/ApolloAuto/videos) instead. It's worth someone
digging through it properly if we need a video reference for the team later — most of what's there leans more
product-demo than architecture explainer.

# Summary — where this leaves us

Looking into Apollo showed that not every company on our list is going to describe jobs the same way — a
Baidu-linked company is more likely to mention Cyber RT or EM Planner than ROS 2 or behavior_path_planner, even
though the actual work maps onto the same categories (Perception, Planning, Control, etc.). So we've now got a
second vocabulary to catch postings that would otherwise slip past a purely Autoware-flavoured keyword list.

The dataset comparison rounds this out from a different angle: each of these datasets is built around specific
benchmark tasks (3D object detection, tracking, motion forecasting, segmentation, etc.), and that task-level
language turns out to be the stronger classification signal — more likely to show up in a JD than the dataset
name itself. The dataset names are still worth keeping around, just as a weaker, secondary "this is AV-relevant"
flag rather than a category-deciding one.

