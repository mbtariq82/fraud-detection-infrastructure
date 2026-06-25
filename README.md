# fraud-detection-infrastructure
1) Build a real-time transaction scoring API: receive transactions, compute risk features (velocity, amount deviation, geo anomaly), apply rule engine, and return risk score with <100ms latency.

2) Implement a rule engine: define rules in a DSL/config (if amount > X and velocity > Y then flag), support rule versioning, A/B testing of rule sets, and override capabilities.

3) Create a case management system: flagged transactions become cases, analysts can review/approve/reject, add notes, and the system learns from decisions to improve future scoring.

4) Build a feedback loop pipeline: collect analyst decisions, label transactions, retrain models on new data, validate improved performance, and deploy updated model with canary release.
