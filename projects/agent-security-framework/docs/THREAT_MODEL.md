# Synthetic benchmark threat model

In scope: deterministic influence of untrusted synthetic artifacts on actions
inside mock environments. Out of scope: real accounts, services, credentials,
people, browsers, clouds, production data, host discovery, exploitation,
malware, hack-back, and automated accusations.

All credentials are inert fixture values such as `TEST_TOKEN`. A finding is
eligible only after strict validation, structured-oracle detection, repeated
state-hash replay, and counterfactual confirmation.
