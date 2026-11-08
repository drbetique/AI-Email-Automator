# Roadmap

What is done and what is left for AI Email Automator. Items are grouped by theme and listed roughly in the order they should be tackled. Nothing here has a deadline.

## Done

- [x] Fix `requirements.txt` so a fresh install works (`pandas==2.14.1` does not exist; unused packages removed).
- [x] Use the Claude API (Anthropic SDK) for the optional AI features, with the model set by `ANTHROPIC_MODEL`.
- [x] Match rule-based keywords as whole words ("they" is no longer social, "window" is no longer spam).
- [x] Split Gmail message parsing into testable functions.
- [x] Add unit tests for the classifier, the AI path, the Claude call and Gmail parsing.
- [x] Add CI that compiles the code and runs the tests on Python 3.10 and 3.12.
- [x] Remove buttons and options that did nothing.
- [x] Correct the privacy note in the README.

## Correctness

- [ ] Classify each email once and keep the result in `st.session_state`. Today every Streamlit rerun (any button press) calls the model again for every email.
- [ ] Validate the model's JSON: reject categories other than urgent, work, social and spam, and fall back to the rules instead of failing.
- [ ] Reply to the right address: use the `Reply-To` header when present, and set `In-Reply-To` and `References` so the reply stays in the same thread.
- [ ] Handle messages with only HTML bodies by converting them to text properly instead of stripping tags with a regex.
- [ ] Read the sender's display name and address with `email.utils.parseaddr` instead of a regex.
- [ ] Show a clear message when the Gmail token has expired or been revoked, and offer to sign in again.

## Gmail features

- [ ] Implement Mark as spam and Archive with the Gmail `modify` scope, and request that scope only when the user turns the feature on.
- [ ] Let the user choose how many messages to load, which label to read, and whether to include read messages.
- [ ] Page through older messages.
- [ ] Apply a Gmail label for the chosen category.

## Privacy and security

- [ ] Store the OAuth token in the operating system's keyring instead of `token.pickle`.
- [ ] Remove quoted reply history and signatures before text is sent to the model.
- [ ] Add a visible switch that shows whether the model is on, and what will be sent to it.
- [ ] Support a local model, so no email text has to leave the machine.
- [ ] Offer a cheaper model option for classification and keep the larger model for drafting replies.
- [ ] Use structured outputs for the classification result instead of parsing JSON from text.
- [ ] Redact addresses, phone numbers and long numbers from text sent to the model.
- [ ] Add a short `SECURITY.md` explaining how to report a problem and what data the app handles.

## Classification quality

- [ ] Let the user edit the keyword lists and the reply templates from the sidebar and save them.
- [ ] Keep a small set of labelled sample emails and report accuracy for the rules and for the model.
- [ ] Support more than one language in the rule-based keywords.
- [ ] Let the user correct a category and use the corrections to adjust the rules.

## Structure and quality

- [ ] Move the code into a package with a `src` layout and an entry point.
- [ ] Separate the Streamlit page from the logic so the logic has no UI dependency.
- [ ] Add type hints and run a type checker in CI.
- [ ] Add a linter and formatter configuration and run them in CI.
- [ ] Pin and lock the dependencies, and enable Dependabot.
- [ ] Add an integration test that runs the app with Streamlit's testing helper against sample emails.
- [ ] Report test coverage in CI.
- [ ] Replace `print` calls with `logging`.

## Packaging and demo

- [ ] Add a Dockerfile.
- [ ] Deploy a public demo that uses sample emails only and never asks for Gmail access.
- [ ] Record a new demo video and add it to the README.
- [ ] Add a release with a changelog.
