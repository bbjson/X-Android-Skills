---
name: image-loading
description: >-
  Load, cache and display images at the size they are drawn: one shared loader, bounded decode,
  correct orientation, explicit cache keys and a real failure state. Use when showing remote
  images, when a list of images janks or OOMs, when a photo appears rotated, when the same URL
  loads twice, or when deciding what to keep in memory versus disk.
license: Apache-2.0
metadata:
  domain: platform
  level: advanced
  sources:
    - android-developers (bitmap decoding, ExifInterface, re-expressed)
    - coil (documented API surface, re-expressed)
    - this-repo (gap analysis: camera captured images, nothing displayed them)
---

# Image Loading

One decision: **the decoded bitmap size and the cache identity.** Everything else — rotation, OOM,
flicker, "why did it reload" — follows from those two.

## Use when

- Displaying remote or locally captured images anywhere, including lists and grids.
- A grid or feed janks, allocates heavily, or dies with `OutOfMemoryError`.
- A photo from the camera or gallery shows rotated or squashed.
- The same image is downloaded twice, or a reload happens on every scroll back.
- Deciding cache size, cache keys, placeholders or crossfade.

## Do not use when

- Capturing the image (preview, lens switching, capture lifecycle) → `camera`.
- Choosing the container size, `contentScale` or list item layout → `compose-core`,
  `lazy-layouts`.
- Asset format and bundle size decisions → `app-size`.
- Screenshot/visual regression of the rendered result → `screenshot-testing`.

## Rules

1. **One `ImageLoader` per app, provided by DI.** A loader created per screen or per composable
   discards the memory and disk caches — the two things that make images feel instant.
2. **Give the request a size.** Coil infers it from the layout constraints; an unbounded parent
   (for example a height-less item in a scrollable) has no size, so the bitmap decodes at source
   resolution. Set an explicit `size` for large sources, and constrain the composable.
3. **Decode to the drawn size, not to the source size.** A 4000px photo in a 96dp row should never
   exist as a 4000px bitmap; downsampling at decode time is the difference between 60 fps and a GC
   pause.
4. **Cache identity is explicit when it can collide.** The URL is the default key; when the same URL
   returns different bytes (avatar changes, signed URLs, edited photo), add a version or use an
   explicit `memoryCacheKey`/`diskCacheKey` and invalidate the old one.
5. **Orientation is applied from EXIF by the loader.** If you decode manually with `BitmapFactory`,
   read `ExifInterface` and rotate — browsers, galleries and cameras all produce rotated files with
   upright pixels absent.
6. **`allowHardware(false)` only when you need pixels.** Reading colours, applying a software filter
   or drawing the bitmap into a software canvas requires it; leaving it on everywhere costs memory
   bandwidth for no benefit.
7. **Every image has a placeholder, a failure state and a size-stable container.** A layout that
   grows when the bitmap arrives shifts every item below it.
8. **Prefer a bounded disk cache with a documented size, and respect HTTP cache headers.** An
   unbounded disk cache is a storage complaint waiting to happen; ignoring headers re-downloads.
9. **Clear caches on logout.** Memory and disk caches survive the session; the next user must not
   see the previous user's avatar.
10. **Animated content is opt-in and bounded.** Decoders for GIF/video frames belong to the images
    that need them, with a size cap; an animated GIF in a list decodes every frame.
11. **Prefetch is anticipation, not a queue of everything.** Enqueue the next page's images when the
    page is known, not the whole feed at start.
12. **Tests and previews use a fake loader/painter** so screenshot tests are deterministic and do
    not hit the network.

## Procedure

1. Configure the single loader (memory cache, disk cache directory and size, decoders).
2. For each screen, fix the container size and pass an explicit size where the source is large.
3. Add placeholder/error content and keep the container size stable.
4. Add cache invalidation for content that can change behind a stable URL.
5. Clear caches on logout; cap the disk cache.

## Checklist

- [ ] Single app-wide loader from DI.
- [ ] Request size is bounded and matches the drawn size.
- [ ] No full-resolution decode of large sources.
- [ ] Cache key invalidation where a URL's content can change.
- [ ] EXIF orientation handled (loader or manual decode).
- [ ] `allowHardware(false)` only where pixels are read.
- [ ] Placeholder, error state, and size-stable container.
- [ ] Disk cache bounded; HTTP headers respected.
- [ ] Caches cleared on logout.
- [ ] Animated decoding opt-in and size-capped.
- [ ] Deterministic fakes in tests/previews.

## Anti-patterns

| Symptom | Wrong | Correct | Why |
|---|---|---|---|
| OOM scrolling a grid | decode at source size | request size = drawn size | full-res bitmaps retained |
| Memory never reused | loader per screen | one singleton loader | caches discarded |
| Stale avatar | URL as key forever | versioned key | cached bytes reused |
| Photo rotated | `BitmapFactory` only | apply EXIF orientation | pixels are not upright |
| List jumps when loaded | unconstrained container | fixed aspect/size | layout shift |
| Next user sees old images | no cache clear | clear on logout | data leak |
| Battery drain on GIF list | animated decoder everywhere | opt-in, capped | per-frame decode |

## Verify

```bash
./gradlew :app:assembleDebug
adb -s <serial> shell dumpsys meminfo <pkg> | head -30          # before/after scrolling a gallery
adb -s <serial> logcat -d | grep -iE 'OutOfMemory|coil' | tail -20
./gradlew :app:testDebugUnitTest --tests '*Image*'
```

Expected: memory stays flat while scrolling a long image list (no monotonic growth, no
`OutOfMemoryError`), rotated photos display upright, and scrolling back to an item does not trigger a
second network request.

## References

- Coil `ImageLoader`, `ImageRequest.size`, `memoryCacheKey`, `allowHardware`, `ImageRequest.Builder`
- `BitmapFactory.Options.inSampleSize`, `ExifInterface`
- `MemoryCache`, `DiskCache` sizing
