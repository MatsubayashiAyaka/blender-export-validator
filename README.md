# Export Validator (Blender Add-on)

Export Validator is a Blender add-on that validates mesh data **before FBX export**.
It detects common problems that frequently cause issues in real-time pipelines (Unity / Unreal Engine / etc.).

This repository is intended as a **Technical Artist portfolio project**:
- Blender-native UX (non-modal Sidebar panel)
- Non-destructive (no auto-fix)
- Practical validations for game assets
- Robust selection / focus workflow

---

## Features

### Geometry
- **Face Orientation** (flipped / inconsistent faces)
- **Ngons**
- **Loose geometry** (loose vertices / edges)

### Transforms
- **Non-uniform scale**
- **Negative scale**
- **Unapplied transforms**

### UV / Data
- **Missing UV**
- **Too many UV maps**

### Workflow
- Export-time **Gate dialog** (prevents forgetting)
- Sidebar panel with filtering: **Severity / Object / Type**
- **Check Faces** button (Face Orientation / Ngons): select + focus problematic faces
- **Rescan** on demand (no background handlers)

### Stability
- VIEW_3D context-safe operator calls
- Optional workaround for Blender 4.2 Node Wrangler poll traceback (enabled by default in this release)

---

## Supported Versions
- Blender **3.6+**
- Tested on Blender **4.2.x**

---

## Installation (Release ZIP)
1. Download `export_validator_v1.0.0_blender-addon.zip` from Releases
2. Blender → **Edit** → **Preferences** → **Add-ons**
3. **Install…** → select the ZIP
4. Enable **Export Validator**

Panel location:
- 3D Viewport → Sidebar (N) → **Tool** → **Export Validator**

---

## Usage

1. Select one or multiple mesh objects
2. Click **Rescan**
3. Use filters if needed
4. Click issues to select objects
5. For Face Orientation / Ngons, click **Check Faces**
6. Fix manually
7. Export via **File > Export > FBX (.fbx)** (Gate dialog appears)

---

## Technical Notes (Face Orientation)
- **Closed mesh**: centroid-based absolute test (dot(normal, center→face) < 0)
- **Open mesh**: neighbor consistency / winding-based relative test

---

## License
MIT License. See `LICENSE`.

---

## Author
Matsubayashi Ayaka

---

## Technical Architecture
### Goals
- Prevent FBX export problems before engine import
- Reduce iteration time for artists
- Provide Blender-native UX (non-modal, non-destructive)

### Implementation Details
- Blender Python API
- bmesh topology analysis
- Hybrid Face Orientation detection:
  - Closed mesh → centroid based absolute test
  - Open mesh → neighbor consistency / winding test
- VIEW_3D context-safe operator overrides
- No background handlers (manual rescan only for performance)
- Node Wrangler compatibility workaround (Blender 4.2)

### Design Decisions
- No auto-fix (artists stay in control)
- Select & Focus workflow only
- Sidebar panel instead of modal windows
- Minimal UI for production speed

### Why this matters
In real projects, fixing issues **inside Blender before export** saves significant time compared to debugging after importing into a game engine.

This tool demonstrates:
- Pipeline thinking
- Tool design for artists
- Practical geometry analysis
- Stable Blender add-on architecture
