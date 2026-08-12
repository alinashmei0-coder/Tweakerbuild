// Harmless smoke-test tweak.
// This is intentionally minimal. Replace the target/process information
// with information you are authorized to modify.

%hook UIApplication

- (void)applicationDidBecomeActive:(id)application {
    NSLog(@"[TwaekerBuild] test tweak loaded");
    %orig;
}

%end
