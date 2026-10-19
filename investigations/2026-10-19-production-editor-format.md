# Production editor format failure

Expected: actual Harness² accepts bounded guidance edits. Observed: all three editor calls rejected as non-strict JSON; selected guidance equals baseline. Framework success is not adaptation success. Different downstream outcomes under identical guidance cannot be credited to refinement.

Hypotheses: (1) exact Markdown fences around valid JSON; (2) malformed/truncated JSON; (3) valid JSON but invalid guidance content/size. Distinguish by replaying saved responses through the existing exact-single-fence normalizer and strict parse_editor_response. If normalization plus strict validation passes, (1) is supported and (2)/(3) are contradicted for those outputs. Otherwise retain each specific rejection. No new provider calls; do not change original receipts or claim replayed edits were live adopted.

## Results and change

Exact-fence normalization exposed a second formatting issue in all three responses: the guidance string lacked a trailing newline. The saved-response parser therefore still rejected them. No content-size or truncation issue was found. Added exact-single-fence handling and host-added final newline; extra prose, duplicate/extra keys, non-string guidance, code markup and bounds remain rejected. All three saved proposals now validate and differ from baseline. This is syntax recovery only, not proof of useful guidance or successful live adoption.

Primary evidence: production-editor-format-replay.json (fence-only failed); production-editor-canonical-replay.json (canonical parsing passed). Four adapter tests pass including actual fake-provider recursion and narrow format handling. Retain original live receipts unchanged in substance, with explicit interpretation added: adopted guidance was identical to baseline. Next run needs fresh inference; replay cannot substitute for a responsive editor seeing altered upstream stages.
