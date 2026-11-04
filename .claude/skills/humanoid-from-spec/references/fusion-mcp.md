# Fusion 360 through MCP

Fusion is the CAD of record, but it is slow, and the MCP calls time out long before Fusion finishes. Work offline
until the spec passes, then build in short calls.

## Connecting

Fusion ships the MCP server; there is nothing to install. In Fusion: **Preferences -> General -> API ->
"Fusion MCP Server (runs locally on this device)"**, which is off by default. Tick it and OK. The port is beside
it (27182 by default) and the line under it says whether the server is running. No other API preference matters:
Developer Tools and the debugging ports are unrelated, and there is no add-in to load.

It speaks streamable HTTP at `http://127.0.0.1:<port>/mcp`, registered in the repo's `.mcp.json`:

```json
{ "mcpServers": { "fusion": { "type": "http", "url": "http://127.0.0.1:27182/mcp" } } }
```

Claude Code reads `.mcp.json` when a session starts, so a session already running will not see it until restarted.
To check the server without a restart, POST an `initialize` to that URL: it answers with an `MCP-Session-Id`
header, which later calls pass back.

Four tools (Fusion 2706.1.17, checked 2026-11-03):

| tool | what |
|---|---|
| `fusion_mcp_execute` | `featureType`: **script** (below), `document`, `purchase`, `editImage`, `generatePowerpoint`, `previewImage` |
| `fusion_mcp_read` | `queryType`: `apiDocumentation` (searchable), `screenshot` (direction, size, anti-aliasing), `document`, `projects`, `licensing`, `activeCommand` |
| `fusion_mcp_update` | `undo`, `redo` |
| `fusion_mcp_electronics_read` | 50 `electronics.*` classes; needs an Electronics document |

`fusion_mcp_read` with `queryType: "apiDocumentation"` searches the Fusion API docs from inside the tool: use it
before writing a script, rather than guessing at a class or member name.

## Calling the build module

`fusion_mcp_execute` with `featureType: "script"` takes `{"script": "...", "readOnly": true|false}`. The script
must define `run` with exactly one argument; whatever it prints comes back as the tool's output, and an exception
comes back as the error. **Do not catch exceptions in `run`** -- a caught one loses where and why it failed.

`readOnly` is enforced, not taken on trust: a read-only script that tries to change the design fails with "Cannot
modify the design from a read-only context", and it must also avoid `Application.executeTextCommand`. In exchange,
a read-only script runs even while a command dialog is open, which is the way to inspect state mid-command. A
normal script cannot: it returns an error saying so, and the user has to close the dialog first.

Each call imports the build module fresh:

```python
import sys, importlib
P = r'<repo>\cad\fusion'
if P not in sys.path:
    sys.path.insert(0, P)
import figlib, build
importlib.reload(figlib); importlib.reload(build)

def run(_context: str):
    print(build.new_document())
    for n in build.spec()['links']:
        print(build.link(n))
    print(build.parametric())
    print(build.joints())
    print(build.status(), build.verify())
```

First `python -I tools/export_prints.py` (it writes `spec/parts.json`, or `parts_<recipe>.json` under `MILLI_RECIPE`), and `python -I tools/verify_fusion.py write`. A whole robot takes about 5 minutes in one call: a request can outlast the client's default timeout, so give it 10.

`cad/fusion/full_build.py` is all of it for a variant: build, verify, interference, pictures, save, close. `tools/fusion_call.py` runs it if the session hasn't loaded Fusion's server as a tool.

| call | does |
|---|---|
| `build.new_document()` | a new Z-up design with no timeline. **Every full build: rebuilding a link in place keeps its old name, as `trunk 1`** |
| `build.link(name)` | the link's component: one body per printed part (joined, hollow, with its pockets and holes), one per bought part, every screw head |
| `build.parametric()` | turns the timeline on: 17 items instead of 1,800. Joints need it. With no timeline, `features.add()` returns None: name nothing from it |
| `build.joints([names])` | as-built revolute joints with limits. **Exactly on a limit, `rotationValue` refuses and stays put:** test at 98 % |
| `build.status()` | links, joints, timeline length, and problems (body counts against the spec, unhealthy features) |
| `build.verify()`, `build.verify_points()` | each printed body against the STL: its volume, then 1,500 points each, read by `python -I tools/verify_fusion.py compare` |
| `build.pose({...})`, `build.show(skins=False)` | pose the model; hide the covers to see inside |
| `build.render(path, view)` | orthographic picture; reports whether the file was written |
| `build.export_stl(folder)` | one STL per link at the zero pose, for the URDF (millimetres; the writer rescales) |

## After a build

`design.analyzeInterference` over all occurrences takes seconds and finds what offline checks skip. Explain every clash left. On milli what's left is: horn seats (drawn 0.5 mm
into their plates), screw heads in their own counterbores, bearing races 0.05 mm over a horn. Anything else is a real problem. Then take a picture from every side, the top and
underneath, in shaded style, and read them.

A script with `readOnly` is refused any change, naming that as the reason: read errors to their end before chasing them.

## Timeouts and speed

- With a timeline: one link per call. A full build is about 1,800 timeline features, and in a big document one link with many cut
  prisms took 5-10 minutes. Build with none instead.
- After a timeout Fusion carries on. Poll with read-only scripts (`"readOnly": true`) that print the link's bodies
  or `status()`. They time out too while Fusion is busy; keep asking.
- Do offline work while Fusion builds: renders, videos, docs.
- Keep cuts few and convex: each is a sketch, an extrusion and a combine.
- Rebuild only the changed links and their joints. Start a fresh document only when most links change.

## Save and export

**Save each finished model, then close it, before starting the next:** a build opens a new document, and several open at once is what makes Fusion crawl. Variants of one robot share a hub folder (`my-projects` / `duck-droids`), each named `duck-droids <recipe>`, and go in the repo as `cad/duck-droids-<recipe>.step` and `.f3d`.

- Save into the hub. Find the project by name in `app.data.activeHub.dataProjects` (`app.data.activeProject` can
  raise when no project is selected). Make or find a folder (`rootFolder.dataFolders.add('<name>')`), then
  `doc.saveAs(name, folder, description, '')`. Check `doc.isSaved` and `dataFile.versionNumber`.
- The root component takes the document's name only on save; before that the STEP's top product is
  "(Unsaved)". So save first, then export:
  - `exportManager.createSTEPExportOptions(path)` writes `cad/<name>.step`. **Straight after a first save it wrote an empty file and reported success, and Fusion also refuses to reopen a file that new. Close it, then in a later call open it from the hub and export (`cad/fusion/export_step.py`); count the `MANIFOLD_SOLID_BREP`s;**
  - `createFusionArchiveExportOptions(path)` writes `cad/<name>.f3d`, the native design with its timeline and
    joints;
  - `export_stl` writes the URDF meshes.
- Renaming: rename appearances by collecting the matching names first, then renaming, and repeat until none are
  left. Renaming re-sorts the collection, so a single pass skips some. Then grep the STEP for the old name.

## Pictures

`viewport.saveAsImageFile` and the MCP screenshot can return success and write nothing (with the PC's screen asleep,
or a moved joint's position uncaptured). `build.render` deletes the target first and reports `written`. When Fusion
will not render, `tools/render_pose.py` draws the same shapes offline with the same framing.

## Memory

Fusion held about 10 GB with six full builds open. Build in one document, save it, do every export, and tell the
user when Fusion can be closed. Before stopping the process, check the document is saved (`isModified` false).
Unsaved "Untitled" documents are lost; Fusion offers to recover them on the next start.
