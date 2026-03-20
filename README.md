# ⚽ Tracking to Event Studio v2.0

A professional-grade football analytics dashboard that transforms raw tracking data into meaningful event feeds (Passes, Shots, Recoveries) with real-time 2D visualization and tactical build-up analysis.

![Dashbord Preview](file:///Users/bishalmahatchhetri/.gemini/antigravity/brain/c31c3ece-3708-445c-b75f-6305b8868a0b/analysis_results_1774007616030.png)

## 🌟 Key Features

### 📍 2D Event Visualizer
Instantly see the spatial distribution of events. Every pass is rendered with directional arrows, and shots are highlighted with glowing tactical markers.

### 🎬 Animated Match Replay
Don't just see the data—watch it. Our high-performance canvas engine replays player tracking data frame-by-frame, allowing you to analyze positioning, spacing, and movement patterns.

### ⚽ Automated Build-Up Analysis
The "Coach's Choice" feature. The system automatically identifies shots and goals, then traces back the entire possession chain to show you the exact sequence of passes and recoveries that led to the moment.

### 🚀 Direct File Upload
Supports direct CSV uploads for Home and Away tracking data. No data directory lock-in; just upload and analyze.

---

## 🛠️ Quick Start (Docker)

The fastest way to get started is using Docker:

1. **Build the image**:
   ```bash
   docker build -t tracking-to-event .
   ```

2. **Run the dashboard**:
   ```bash
   docker run -p 8000:8000 tracking-to-event
   ```

3. **Open Explorer**:
   Navigate to [http://localhost:8000](http://localhost:8000)

---

## 🏗️ Project Architecture

- **Backend**: FastAPI (Python) powers the event detection engine and frame-sampling API.
- **Frontend**: Vanila JS + CSS for a lightweight, high-performance "Glassmorphism" UI.
- **Engine**: Rule-based possession detection using coordinate-geometry and velocity heuristics.

---

## 📜 Credits & Attribution

This project is a heavily modernized and expanded version of the original exploration by **John Comonitski**.

- **Original Repository**: [JohnComonitski/TrackingDataToEventData](https://github.com/JohnComonitski/TrackingDataToEventData.git)
- **Contribution**: We have added the entirely new 2D pitch visualizer, the animated replay system, the build-up chain analysis, and the modern web dashboard interface while preserving and enhancing the core event detection logic.

---

## 🤝 Contribution

Feel free to open issues or submit PRs! This tool is built by and for football analysts who love data.

---

*Built with ❤️ for the Football Analytics Community.*
