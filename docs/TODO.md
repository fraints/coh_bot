
## Add summary of how everything works

## Migrate logic into library, not just debug script

## Extract hp and end data

## Extract names and other text

## Write tests for images

## Speed up detection

Running the test suite on team1.jpeg with the flag enabled yields the following metrics: [Timing] Detect: 5529.1ms | Player: 0.1ms | Target: 0.0ms | Team: 86.9ms | Save: 3.4ms

As expected, the initial detector.detect(img) pass is consuming over 98% of the processing time (around 5.5 seconds). This happens because the detector runs over 20 distinct cv2.matchTemplate sweeps—a relatively expensive mathematical pass—over the entire uncropped 4K resolution screenshot.

By comparison, the new geometrically rigid logic we built for tracking the Team Window takes roughly 85 milliseconds, and parsing the Player and Target windows takes less than 0.1 ms!

When we transition to real-time processing in the bot loop, the obvious massive optimization will be caching locations frame-to-frame. Rather than sweeping the entire 4K screen for the xp_wheel every cycle, the bot will only run template matching within a tiny 100x100 regional box (ROI) centered around where the window was detected on the previous frame.

