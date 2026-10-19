# Recovery restart assertion

Observed: the first combined run passed 26/27 tests. The interrupted-recovery test compared entire frames and failed with time 0.0 versus 0.85.

Competing explanations: a discontinuous pose, or a correct new clip with a reset local timeline. Field comparison found joints_equal=True, contacts_equal=True and stop_equal=True; only the local clip time changed. The contract requires exact joints/contacts at the starting boundary and a fresh 0–2 second timeline. The test now asserts those independently. No motion implementation change was needed for this failure. Sol subsequently ran all 11 runtime tests successfully, including explicit recovery, interrupted recovery, stale response rejection and fresh restart.
