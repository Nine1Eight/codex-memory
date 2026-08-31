# SigilAGI Glyph Schema

## Purpose

The SigilAGI glyph schema converts object labels into symbolic reasoning units.

The core transformation is:

```text
object label → glyph → meaning → scene role → review level
This gives the AI system a compressed symbolic structure that can be inspected by humans.
Object Glyph Record
Each detected object is represented as:
JSON
{
  "index": 1,
  "label": "person",
  "glyph": "☉",
  "meaning": "actor / observer / intent",
  "role": "human subject",
  "risk": "human-review",
  "detection_source": "user_label_or_detector_output"
}
Required Fields
Field
Meaning
index
Object order in the detected list
label
Normalized object name
glyph
Symbol assigned to the object
meaning
Semantic compression of the object
role
Scene-level function of the object
risk
Review level
detection_source
Where the object label came from
Review Levels
Risk Level
Meaning
low
Normal object, low concern
medium
Object may affect interpretation
human-review
Human subject or sensitive reasoning case
privacy-review
Privacy-sensitive object or identity-adjacent object
high-review
Potentially hazardous object label
unknown
Object has no custom glyph mapping yet
Current Glyph Set
Object
Glyph
Meaning
Review
person
☉
actor / observer / intent
human-review
human
☉
actor / observer / intent
human-review
face
◉
identity-sensitive visual feature
privacy-review
door
⛩
boundary / transition / access
low
window
▤
visibility / opening / observation
low
phone
☏
communication / signal / record
low
camera
◈
recording / observation / evidence
privacy-review
car
⟡
movement / transport / force
medium
truck
⟡
movement / transport / force
medium
vehicle
⟡
movement / transport / force
medium
bag
▣
container / carried item / storage
low
backpack
▣
container / carried item / storage
low
light
✦
visibility / signal / attention
low
knife
⚠
possible danger / sharp object / review required
high-review
gun
⚠
possible weapon / danger / review required
high-review
weapon
⚠
possible danger / review required
high-review
dog
♞
animal / movement / alertness
medium
cat
♘
animal / movement / presence
low
paper
▧
document / record / instruction
low
document
▧
document / record / instruction
low
money
¤
value / transaction / resource
medium
wallet
▨
identity / value / personal property
privacy-review
key
⌘
access / permission / control
medium
unknown object
◇
unknown object / unmapped symbol
unknown
Relationship Format
Relationships are represented as both glyph logic and plain language.
Example:
JSON
{
  "symbolic": "☉ near ☏",
  "plain": "A human subject and a communication or recording device appear in the same scene."
}
Safety Rules
SigilAGI must not claim:
Identity
Intent
Guilt
Legal status
Medical status
Exact danger level from uncertain object labels
SigilAGI should say:
Possible
Unclear
Needs review
Not enough evidence
Human review required
Hackathon Relevance
This schema shows how Gemma 4 can reason over structured symbolic input instead of raw image captions alone.
The project demonstrates:
Object-to-glyph compression
Symbolic visual reasoning
Transparent AI traces
Human-review safety boundaries
Assistive scene interpretation
