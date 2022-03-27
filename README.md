# meand23

## Installation

`pip install meand23`

## Usage

Log in, identify profiles with a processed kit, and print each profile's genome:

```
import json
m23 = MeAnd23()
m23.login('your@gmail.com', 'your_password')
profiles = m23.profiles()
profiles_with_kit = []
for profile in profiles:
    try:
        m23.use_profile(profile)
        m23.chromosome(1)
        profiles_with_kit.append(profile)
    except MissingKitError:
        pass

for profile in profiles_with_kit:
    m23.use_profile(profile)
    for gene in m23.genome():
        print(gene)

```