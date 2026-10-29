## Results matrix

| Drift | Outcome | Rows affected | schema_snapshot_diff | pydantic_loose | pydantic_strict | statistical_profile |
|---|---|---|---|---|---|---|
| rename_rarity | failed_loudly | - | yes | yes | yes | no |
| drop_equipped_slot | failed_loudly | - | yes | yes | yes | no |
| local_time_without_offset | passed_with_corruption | 1000 | no | no | yes | no |
| empty_equipped_slot | passed_with_corruption | 205 | yes | no | yes | yes |
| add_column | passed_clean | 0 | yes | no | yes | no |
| type_change_level | passed_clean | 0 | yes | no | no | no |
| new_enum_value | passed_with_corruption | 20 | no | yes | yes | no |
| stats_become_list | failed_confusingly | - | yes | yes | yes | no |
| durability_scaled | passed_with_corruption | 1000 | no | no | no | yes |
| **Total caught** | | | 6/9 | 4/9 | 7/9 | 2/9 |

## Pipeline errors

| Drift | Label | Error |
|---|---|---|
| rename_rarity | failed_loudly | `KeyError: 'rarity'` |
| drop_equipped_slot | failed_loudly | `KeyError: 'equipped_slot'` |
| stats_become_list | failed_confusingly | `TypeError: list indices must be integers or slices, not str` |

## Caught by only one detector

- **local_time_without_offset**: only pydantic_strict
- **type_change_level**: only schema_snapshot_diff
- **durability_scaled**: only statistical_profile
