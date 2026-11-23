---
name: camera
description: >-
  Implement camera capture with CameraX bound to the right lifecycle: preview into Compose, capture,
  rotate and mirror correctly, switch lenses without leaking, and handle permission denial. Use when
  adding camera or video capture, when the preview is black or rotated, when switching cameras crashes,
  or when capture fails only after rotating the device.
license: Apache-2.0
metadata:
  domain: platform
  level: specialized
  sources:
    - android-skill (camerax)
    - agent-skills-standard (android-legacy-security)
    - kotlin-footguns (compose-screens-footguns)
    - android-agent-engineering (android-testing)
---

# Camera

Camera is **a resource with an owner and a lifecycle**. Almost every camera bug is a binding that was
not released, or a provider rebuilt at the wrong time.

## Use when

- Adding photo/video capture (CameraX is the default; Camera2 only for specialty needs).
- Preview is black, stretched, rotated or mirrored incorrectly.
- Switching front/back camera crashes or freezes.
- Capture fails after rotation or after backgrounding.
- Handling `CAMERA` permission denial (and `RECORD_AUDIO` for video).

## Do not use when

- The task is picking an existing image (photo picker) — no camera involved.
- The task is scanning a barcode → ML Kit / CameraX analyzer, not this skill's capture path.
- The task is video playback → `media3`.
- Permission UX, pickers and URI grants → `permissions-and-pickers`.
- Displaying, rotating or caching the captured image → `image-loading`.

## Rules

1. **One `ProcessCameraProvider`, obtained asynchronously and cached.** `ProcessCameraProvider.getInstance(context)`
   returns a `ListenableFuture`; await it once per process (or per ViewModel), not per recomposition.
2. **Bind every use case with `bindToLifecycle(owner, selector, preview, capture, …)`**, where `owner` is
   a `LifecycleOwner` that actually matches the visible surface (Activity/Fragment/`LocalLifecycleOwner`).
   Binding to an owner that outlives the screen keeps the camera on after the user leaves.
3. **Unbind before rebinding when switching lenses.** `cameraProvider.unbindAll()` then rebind with the
   new `CameraSelector`, and only after the previous capture session completed.
4. **Preview `SurfaceRequest`/`PreviewView` must be created once.** In Compose, either use the official
   `PreviewView` interop or a dedicated `SurfaceRequest` handler; recreating the surface per
   recomposition produces black previews.
5. **Rotation: use the target rotation, not the device rotation guess.** Set
   `preview.targetRotation` / `imageCapture.targetRotation` from the display, and read
   `imageProxy.imageInfo.rotationDegrees` for analysis. A landscape-captured portrait photo is a
   rotation bug, not a camera bug.
6. **Mirror only front-camera preview, never the saved file** (unless the product explicitly wants
   mirrored selfies). Mirroring both is the classic "text reversed" defect.
7. **Capture on `ContextCompat.getMainExecutor()` for UI callbacks, and use a background executor for
   analysis**; never run image processing on the main thread.
8. **Persist the captured file with a `FileProvider` URI** (see `component-exposure`), and take a
   persistable URI permission if the file must survive the session.
9. **Handle permission states explicitly:** granted, denied once, denied permanently
   (`shouldShowRequestPermissionRationale` false) — the last needs a settings deep link, not another
   request that silently no-ops.
10. **Release on lifecycle stop, rebind on start.** Backgrounding must stop the camera; returning must
    restore the preview without re-requesting permission.
11. **Test on a physical device.** Emulators fake camera input (a pattern, not a sensor); rotation,
    mirroring and autofocus failures only appear on hardware.

## Procedure

1. Add permission request first; branch on all three states (rule 9).
2. Create the preview surface once; keep a reference in a state holder.
3. Await the provider once; bind preview + capture to the visible lifecycle owner.
4. Wire lens switch: `unbindAll()` → new selector → bind.
5. Set target rotation from the display on both use cases.
6. Capture → write to cache → `FileProvider` URI → optional persistable permission.
7. Verify: rotate, background/foreground, switch lens, deny permission, capture, and re-open from the
   picker.

## Checklist

- [ ] Provider awaited once and cached, not per recomposition.
- [ ] All use cases bound to the correct visible `LifecycleOwner`.
- [ ] `unbindAll()` before lens switch.
- [ ] Preview surface created once.
- [ ] Target rotation set from the display; EXIF rotation correct.
- [ ] Front camera mirroring applied to preview only.
- [ ] Capture callbacks on main, analysis off main.
- [ ] Output file via `FileProvider` + permission handling.
- [ ] Permission denial (incl. permanent) handled with a settings path.
- [ ] Camera released on stop, rebind on start.
- [ ] Verified on a physical device.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| Black preview | new surface per recomposition | create once | surface churn |
| Camera stays on after leaving | bind to Activity that outlives screen | screen's lifecycle owner | privacy + battery |
| Crash on lens switch | rebind without unbind | `unbindAll()` first | conflicting sessions |
| Sideways photo | ignore rotations | target rotation + EXIF | wrong orientation |
| Reversed text | mirror preview and file | mirror preview only | written content reversed |
| Silent no-op | request permission repeatedly | settings deep link when permanent | user stuck |
| Emulator "works" | test on emulator | physical device | fake sensor |

## Verify

```bash
adb -s <serial> shell pm grant <pkg> android.permission.CAMERA
adb -s <serial> logcat -c && adb -s <serial> logcat -d | grep -iE "CameraX|CameraDevice|CaptureSession" | tail -20
adb -s <serial> shell dumpsys media.camera | head -20    # after leaving the screen: no active client
```

Expected: preview visible, captured file orientation matches the device, and after leaving the screen
`dumpsys media.camera` shows no active client.

## References

- CameraX `ProcessCameraProvider`, `bindToLifecycle`, `Preview`/`ImageCapture`/`ImageAnalysis`
- `FileProvider` for output files; EXIF orientation
