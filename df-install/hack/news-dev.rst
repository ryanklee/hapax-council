DFHack 53.11-r2
===============

Fixes
-----
- `autoclothing`, `autoslab`, `tailor`: orders will no longer be created with a repetition frequency of ``NONE``
- `gui/rename`: skip ``NONE`` when iterating through language name options
- `quickfort`: work orders will no longer be created with a repetition frequency of ``NONE``

Misc Improvements
-----------------
- General: DFHack will unconditionally use UTF-8 for the console on Windows, now that DF forces the process effective system code page to 65001 during startup

Structures
----------
- reordered XML attributes for consistency: ``ret-type``, ``base-type``, ``type-name``, and ``pointer-type`` now appear first (and in that exact order)


DFHack 53.11-r1
===============

Fixes
-----
- `sort`: correct misspelling of ``PERSEVERENCE``; fixes "hates combat" filter in squad selection screen

Structures
----------
- added codegen support for ``static-wstring`` (``wchar_t *``), required to support DF 53.11


DFHack 53.10-r2
===============

New Tools
---------
- `gui/logcleaner`: graphical overlay for configuring the logcleaner plugin with enable and filter toggles.
- ``logcleaner``: New plugin for time-triggered clearing of combat, sparring, and hunting reports with configurable filtering and overlay UI.

New Features
------------
- `orders`: added search overlay to find and navigate to matching manager orders with arrow indicators
- `sort`:
    - added ``Uniformed`` filter to squad assignment screen to filter dwarves with mining, woodcutting, or hunting labors
    - Add death cause button to dead/missing tab in the creatures screen
- `trackstop`: can now modify pressure plates; permits minecart and creature triggers to be set beyond normal sensitivity

Fixes
-----
- `gui/rename`: added check for entity_id input in get_target function
- `prioritize`: Fix the overlay appearing where it should not when following a unit

Misc Improvements
-----------------
- Core: DFHack now validates vtable pointers in objects read from memory and will throw an exception instead of crashing when an invalid vtable pointer is encountered. This makes it easier to identify which DF data structure contains corrupted data when this manifests in the form of a bad vtable pointer, and shifts blame for such crashes from DFHack to DF.
- `gui/notify`: reduced severity of the missing nemesis records warning if no units on the map are affected.  clarified wording.

API
---
- Added ``Items::pickGrowthPrint``: given a plant material and a growth index, returns the print variant corresponding to the current in-game time.
- Added ``Items::useStandardMaterial``: given an item type, returns true if the item is made of a specific material and false if it has a race and caste instead.
- Added ``Maps::addItemSpatter``: add a spatter of the specified item + material + growth print to the indicated tile, returning whatever amount wouldn't fit in the tile.
- Added ``Maps::addMaterialSpatter``: add a spatter of the specified material + state to the indicated tile, returning whatever amount wouldn't fit in the tile.

Lua
---
- Added ``Maps::addItemSpatter`` as ``dfhack.maps.addItemSpatter``.
- Added ``Maps::addMaterialSpatter`` as ``dfhack.maps.addMaterialSpatter``.

Structures
----------
- added ``original-name`` attributes to all relevant objects
- fixed numerous structure errors
- specific changes:
    - added NONE entries to many enum types (may affect C++ code using switch() statements): abstract_building_reputation_type, adopt_region_stage_type, artifact_claim_type, block_square_event_type, building_profile_acquisition_method, civzone_type, dance_form_context, dance_form_group_size, dance_form_move_type, divination_outcome_type, dungeon_type, dungeon_wrestle_type, embark_finder_option, environment_type, era_type, flow_type, genetic_modifier_type, hf_artifact_action_type, history_event_collection_type, incident_artifact_location_type, incident_type, incident_written_content_location_type, insurrection_outcome, interaction_flags, interaction_source_type, intrigue_corruption_method_type, inventory_profile_skill_type, inv_item_role_type, journey_type, language_name_category, language_name_component, language_word_table_index, load_game_stage_type, main_choice_type, misc_trait_type, musical_form_melody_frequency, musical_form_melody_style, musical_form_purpose, occasion_schedule_feature, occasion_schedule_type, occupation_type, personality_preference_type, plant_material_def, poetic_form_persona_type, poetic_form_persona_type, prepare_rod_stage_type, projectile_type, region_weather_type, report_zoom_type, resource_allotment_specifier_type, save_substage, scale_construction_type, scale_naming_type, scale_type, secretion_condition, simple_action_type, site_dispute_type, squad_order_cannot_reason, squad_order_type, tactical_situation, talk_choice_type, theft_method_type, timbre_type, travel_log_itinerary_type, workquota_frequency_type, world_construction_type, wrestle_attack_type
    - assigned explicit "UNUSED" names to anonymous enum/bitfield members which are unused
    - expanded ``builtin_mats`` to include 640 new elements for CREATURE_1-200, HIST_FIG_1-200, PLANT_1-200, and UNUSED01-40
    - assigned proper placeholder names to ``interface_key`` section labels
    - promoted several inline-defined types to top-level (intrigue_corruption_flag, job_posting_flag, unitproperyplacementst)
    - ``plant_raw.stockpile_growth_flags`` now uses ``ras_crop_flag``
    - added ``entity_raw_flags`` element "SIEGE_SKILLED_MINERS"
    - added ``stockpile_category`` element "ALL"
    - fixed structure layouts for ``adventure_interface_companionsst``, ``caste_raw``, ``entity_position_assignment``, ``message_order_to_perform_actionst``, and ``workshop_graphics_infost``
    - renamed ``army_controller_goal_infiltrate_societyst`` field "agoal_ab_id" to "goal_ab_id"
    - renamed ``creature_graphics_layer`` field "dye_color_iuse_palette_rowndex" to "use_palette_row"
    - renamed ``entity_raw_flags`` enum member "MISSING_UNDERWORLD_DISASTERS" to "MINING_UNDERWORLD_DISASTERS"
    - assigned proper names to ``hf_religious_datast.anon_1``, ``pet_profilest.anon_1``, and ``unit_vision_arcst.anon_1``
    - renamed ``historical_entity`` field "unkarmy_reeling_defense" to "army_reeling_defense"
    - renamed ``history_event_hf_learns_secretst`` field "interaction_effect" to "interaction_source"
    - renamed ``item_craft_graphics_flag`` field "size" to "material"
    - renamed ``lookinfo_spatterst`` field "extend" to "extent"
    - renamed ``personality_ethicst`` field "reponse" to "response"
    - renamed ``personality_facet_type`` enum member "PERSEVERENCE" to "PERSEVERANCE"
    - renamed ``value_type`` enum member "PERSEVERENCE" to "PERSEVERANCE"
    - renamed ``poetic_form_action`` enum member "MakeConsession" to "MakeConcession"
    - renamed ``simple_action_type`` enum member "performe_horrible_experiments" to "performed_horrible_experiments"
    - renamed ``stair_graphics_flag_material`` enum member "FOZEN" to "FROZEN"
    - renamed ``timbre_type`` enum member "PURE\_" to "PURE"
    - renamed ``tissue_style_type`` enum member "PONY_TAILS" to "PONY_TAIL"
    - renamed ``unit`` field "job.siege_boulder" to "job.siege_builder"
    - renamed ``unit`` field "pool_index" to "pool_id"
    - renamed ``viewscreen_choose_start_sitest`` field "def_candidate_nearst" to "def_candidate_near_st"
    - changed ``caste_raw.extracts.blood_state`` and ``caste_raw.extracts.pus_state`` to use the ``matter_state`` enum
    - changed ``d_init.display.track_tile_invert`` and ``d_init.display.track_ramp_invert`` to use a bitfield
    - changed ``interrogation_resultst.relationship_factor`` to use a new enum type (which DF itself actually isn't using yet due to a bug)
    - changed ``intrigue_perspectivest.potential_corrupt_circumstance_target[]`` to contain ``circumstance_id`` unions instead of plain integers
    - changed ``world.buildings.other.WINDOW_ANY`` to specify the correct element type
    - changed ``world.items.other.BAG``, ``world.items.other.BOLT_THROWER_PARTS``, ``world.items.other.ANY_DRINK``, ``world.items.other.ANY_CRITTER``, and ``world.items.other.FOOD_STORAGE`` to specify the correct element types
    - changed ``game.main_interface.last_displayed_hover_inst`` to use the ``main_hover_instruction`` enum
    - changed ``world.raws.music.all[N].m_event[]`` and ``world.raws.music.all[N].context[]`` to hold enums
    - changed ``widget_job_details_button.jb`` to correctly point at a ``job`` instead of a generic pointer
    - changed ``world.worldgen_status.rejection_reason`` to use the ``map_reject_type`` enum
    - changed ``world.history.first_[research]_flag[N]`` to use the various ``knowledge_scholar_flags_N`` bitfields
    - changed the ``history_event`` vmethods ``getSentence`` and ``getPhrase`` to add 2 new boolean arguments (to which the game always passes "true, false")
    - changed the ``interaction_target`` vmethod ``affects_unit`` first parameter from an integer to a unit pointer
    - changed the ``item`` vmethod ``getGloveHandedness`` return type from int8_t to uint32_t
    - changed the ``item`` vmethod ``getAmmoType`` to take no parameters and to return an ``std::string`` by value
    - changed the ``item`` vmethod ``getDyeAmount`` to take an integer parameter
    - changed the ``unit`` vmethod ``getCreatureTile`` to take a boolean parameter
    - add ``ref-target`` attributes to various fields that were missing them, for use by ``gui/gm-editor`` and similar tools
    - changed ``caste_raw.extracts.vermin_bite_chance`` to ``vermin_bite_state`` and changed its type to ``matter_state``
    - changed ``ci_personal_reputation_profilest`` field ``entity_id`` to ``cultural_identity`` (now referring to a ``cultural_identity``)
    - changed ``cultural_identity.events[]`` to ``cultural_identity.rumor_info.events[]``
    - changed ``dance_form`` field ``entity`` to ``event`` (now referring to at a ``history_event``)
    - changed ``dance_form_section`` field ``acts_out_civ`` to ``acts_out_event`` (now referring to a ``history_event``)
    - changed ``entity_burial_request`` field ``civ`` to ``hfid`` (now referring to a ``historical_figure``)
    - changed ``entity_pop_specifierst`` field ``squad_id`` to ``squad_enid`` (now referring to a ``historical_entity``)
    - changed ``gps.color[x][y]`` to ``gps.default_palette.color[x*16+y]``
    - changed ``history_event_modified_buildingst`` field ``modification`` to use a different bitfield ``abstract_building_tower_flag``
    - changed ``itemdef_ammost``, ``itemdef_siegeammost``, ``itemdef_toolst``, ``itemdef_trapcompst``, and ``itemdef_weaponst`` fields "texpos" (and "texpos2") into longer lists of specific fields
    - changed ``knowledge_profilest.known_events[]`` to ``knowledge_profilest.rumor_info.events[]``
    - changed ``relationship_event_supplement`` integer field ``occasion_type`` to ``circumstance`` of type ``unit_thought_type`` (an enum)
    - changed ``relationship_event_supplement`` integer field ``site`` to ``circumstance_id`` field of type ``circumstance_id`` (a union)
    - changed ``relationship_event_supplement`` field ``profession`` to ``reason_id`` field of type ``history_event_reason_id``
    - changed ``scholar_knowledge.knowledge_goal`` bitfield to a union of all ``knowledge_scholar_flags_N`` bitfields (selected by the value of ``scholar_knowledge.research_prject``)
    - changed ``unit.enemy.rumor[]`` to ``unit.enemy.rumor_info.events[]``


DFHack 53.10-r1
===============

New Features
------------
- `gui/notify`: new notification type: missing nemesis records; displays a warning message about game corruption.
- `gui/quickcmd`: added custom command names and option to display command output

Fixes
-----
- `autochop`: the report will no longer throw a C++ exception when burrows are defined.
- `suspendmanager`: Fix the overlay appearing where it should not when following a unit

API
---
- Added ``Burrows::getName``: obtains the name of a burrow, or the same placeholder name that DF would show if the burrow is unnamed.

Lua
---
- Added ``Burrows::getName`` as ``dfhack.burrows.getName``.


DFHack 53.09-r1
===============

New Features
------------
- `tweak`: ``drawbridge-tiles``: Make it so raised bridges render with different tiles in ASCII mode to make it more obvious that they ARE raised (and to indicate their direction)

Fixes
-----
- ``Filesystem::as_string`` now always uses UTF-8 encoding rather than using the system locale encoding

API
---
- ``dfhack.job.getManagerOrderName``: New function to get the display name of a manager order


DFHack 53.08-r1
===============

New Features
------------
- compatibility with DF 53.08


DFHack 53.07-r1
===============

New Tools
---------
- `fix/codex-pages`: add pages to written content that have unspecified page counts.
- `gui/keybinds`: gui for managing and saving custom keybindings
- `infinite-sky`: Re-enabled with compatibility with new siege map data.
- ``edgescroll``: Introduced plugin to pan the view automatically when the mouse reaches the screen border.

New Features
------------
- `sort`: Places search widget can search "Siege engines" subtab by name, loaded status, and operator status

Fixes
-----
- `empty-bin`: renamed ``--liquids`` parameter to ``--force`` and made emptying of containers (bags) with powders contingent on that parameter. Previously powders would just always get disposed.
- `sort`:
    - Using the squad unit selector will no longer cause Dwarf Fortress to crash on exit
    - Places search widget moved to account for DF's new "Siege engines" subtab

Misc Improvements
-----------------
- The ``fpause`` console command can now be used to force world generation to pause (as it did prior to version 50).
- `combine`: try harder to find the currently-selected stockpile
- `createitem`: created items can now be placed onto/into tables, nests, bookcases, display cases, and altars
- `keybinding`: keybinds may now include the super key, and are no longer limited to particular keys ranges of keys, allowing any recognized by SDL.

API
---
- ``Hotkey``: New module for hotkey functionality

Lua
---
- The ``Lua interactive interpreter`` banner now documents keywords such as ``unit`` and ``item`` which reference the currently-selected object in the DF UI.
- ``dfhack.hotkey.addKeybind``: Creates new keybindings
- ``dfhack.hotkey.getKeybindingInput``: Reads the input saved in response to a request.
- ``dfhack.hotkey.listActiveKeybinds``: Lists all keybinds for the current context
- ``dfhack.hotkey.listAllKeybinds``: Lists all keybinds for all contexts
- ``dfhack.hotkey.removeKeybind``: Removes existing keybindings
- ``dfhack.hotkey.requestKeybindingInput``: Requests the next keybind-compatible input is saved

Structures
----------
- updated codegen to generate enum trait constants as ``constexpr``


DFHack 53.06-r1
===============

Fixes
-----
- `gui/design`:
    - designating a single-level stair construction now properly follows the selected stair type.
    - adjusted conflicting keybinds, diagonal line reverse becoming ``R`` and bottom stair type becoming ``g``.
- `modtools/set-personality`: use correct caste trait ranges; fixes `gui/gm-unit` being unable to correctly randomize traits or set traits to caste average

Removed
-------
- `infiniteSky`: Temporarily disabled due to incompatibility with changes made as part of DF's siege update

Structures
----------
- added missing field in history_event_artifact_createdst
- fixed incorrect base class on widget_anchored_tile


DFHack 53.05-r1
===============

New Features
------------
- compatibility with 53.05

Fixes
-----
- `sort`: Using the squad unit selector will no longer cause Dwarf Fortress to crash on exit


DFHack 53.04-r1.1
=================

Fixes
-----
- fixed misalignment in ``widgets::unit_list``


DFHack 53.04-r1
===============

New Tools
---------
- `gui/siegemanager`: manage your siege engines at a glance.

New Features
------------
- `item`: new ``--total-quality`` option for use in conjunction with ``--min-quality`` or ``--max-quality`` to filter items according to their total quality

Fixes
-----
- `buildingplan`: Bolt throwers will no longer be constructed using populated bins.
- `RemoteFortressReader`: updated siege engine facing enums for new diagonal directions
- `suspendmanager`: treat reinforced walls as a blocking construction and buildable platform

Misc Improvements
-----------------
- `autolabor`: support for new dying and siege-related labors
- `blueprint`: support for reinforced walls and bolt throwers
- `gui/design`: can now construct reinforced walls
- `quickfort`: support for reinforced walls and bolt throwers
- `stonesense`: queued constructions of reinforced walls are now visible

Structures
----------
- several arrays indexed by enums have been recoded to use the enum's size to size the array so that these will automatically update when the enum is updated, reflecting Bay12 practice


DFHack 53.03-r1
===============

Misc Improvements
-----------------
- Release builds for Linux are now compiled with gcc 11


DFHack 53.02-r2
===============

Fixes
-----
- `buildingplan`: Building costs for reinforced walls are now correct.
- `cleanconst`: do not attempt to clean Reinforced constructions

Misc Improvements
-----------------
- `buildingplan`: Added support for bolt throwers and siege engine rotation.


DFHack 53.02-r1
===============

Misc Improvements
-----------------
- Core: added ``gps`` (``graphicst``) to the set of globals whose sizes must agree for DFHack to pass initialization checks


DFHack 53.01-r1
===============

New Tools
---------
- `fix/symbol-unstick`: unstick noble symbols that cannot be re-designated.
- `resize-armor`: resize armor or clothing item to any creature size.

Fixes
-----
- `autotraining`: squads once used for training then disabled now properly are treated as disabled.

Misc Improvements
-----------------
- `stockpiles`: add support for managing the dyed, undyed, and color filter settings.

Removed
-------
- `fix/archery-practice`: removed from the control panel's bug fixes tab.


DFHack 52.05-r2
===============

Fixes
-----
- `fix/archery-practice`: now splits instead of combining ammo items in quivers, and moves quivers to end of unit's inventory list
- `script-manager`: the ``scripts_modactive`` and ``scripts_modinstalled`` folders of a script-enabled mod will be properly added to the script path search list

Documentation
-------------
- added a clarification link to DF's Lua API documentation to the DFHack Lua API documentation, as a way to reduce end-user confusion


DFHack 52.05-r1
===============

New Tools
---------
- `fix/archery-practice`: combine ammo items in units' quivers to fix 'Soldier (no item)' issue
- `gui/adv-finder`: UI for tracking historical figures and artifacts in adventure mode
- `store-owned`: task owned items to be stored in the owner's room furniture

Fixes
-----
- improved file system handling: gracefully handle errors from operations, preventing crashes.
- `ban-cooking`: bans honey added by creatures other than vanilla honey bee
- `uniform-unstick`:
    - added quivers, backpacks, and flasks/waterskins to uniform analysis
    - the ``--drop`` option now only evaluates clothing as possible items to drop
    - the ``--free`` option no longer redundantly reports an improperly assigned item when that item is removed from a uniform
    - the ``--drop`` and ``--free`` options now only drop items which are actually in a unit's inventory
    - the ``--all`` and ``--drop`` options, when used together, now print the separator line between each unit's report in the proper place
- `zone`: animal assignment dialog now tolerates corrupt animal-to-pasture links.

Misc Improvements
-----------------
- adapt Lua tools to use new API functionality for creating and assigning jobs
- `idle-crafting`: properly interrupt interruptible (i.e. "green") social activities


DFHack 52.04-r1
===============

New Features
------------
- Compatibility with DF 52.04


DFHack 52.03-r2
===============

New Tools
---------
- `autotraining`: new tool to assign citizens to a military squad when they need Martial Training
- `entomb`: allow any unit that has a corpse or body parts to be assigned a tomb zone
- `gui/autotraining`: configuration tool for autotraining
- `husbandry`: Automatically milk and shear animals at nearby farmer's workshops

New Features
------------
- `deathcause`: added functionality to this script to fetch cause of death programatically
- `nestboxes`: allow limiting egg protection to nestboxes inside a designated burrow
- `stonesense`: stonesense now has visible day/night cycle lighting in fortress mode
- `tailor`: tailor now provides optional dye automation

Fixes
-----
- `ban-cooking`: will not fail trying to ban honey if the world has no honey
- `caravan`:
    - in the pedestal item assignment dialog, add new items at the end of the list of displayed items instead of at a random position
    - in the pedestal item assignment dialog, consistently remove items from the list of displayed items
- `confirm`:
    - only show pause option for pausable confirmations
    - when editing a uniform, confirm discard of changes when exiting with Escape
    - when removing a manager order, show correct order description when using non-100% interface setting
    - when removing a manager order, show correct order description after prior order removal or window resize (when scrolled to bottom of order list)
    - when removing a manager order, show specific item/job type for ammo, shield, helm, gloves, shoes, trap component, and meal orders
    - the pause option now pauses individual confirmation types, allowing multiple different confirmations to be paused independently
- `immortal-cravings`: prioritize high-value meals, properly split of portions, and don't go eating or drinking on a full stomach
- `stockpiles`: fixed off-by-one error in exporting furniture stockpiles
- `stonesense`: fixed the announcements not using the bright bool (now matches vanilla DF colors)
- `uniform-unstick`: no longer causes units to equip multiples of assigned items
- ``Units::getReadableName`` will no longer append a comma to the names of histfigs with no profession

Misc Improvements
-----------------
- `devel/hello-world`: updated to show off the new Slider widget

API
---
- ``Job``: new functions ``createLinked`` and ``assignToWorkshop``
- ``Units``: new functions ``getFocusPenalty``, ``unbailableSocialActivity``, ``isJobAvailable``

Lua
---
- New functions: ``dfhack.jobs.createLinked``, ``dfhack.jobs.assignToWorkshop``, ``dfhack.units.getFocusPenalty``, ``dfhack.units.unbailableSocialActivity``, and ``dfhack.units.isJobAvailable``

Structures
----------
- added default values for ``material`` and ``mat_index`` in ``reaction_reagentst`` and ``reaction_productst`` child classes


DFHack 52.03-r1.1
=================

Fixes
-----
- job descriptions of mix dye job will display proper dye names

Structures
----------
- fixed alignment issue in ``entity_raw``


DFHack 52.03-r1
===============

Fixes
-----
- `make-legendary`: ``make-legendary all`` will no longer corrupt souls
- `preserve-rooms` will no longer hang on startup in the presence of a cycle in the replacement relationship of noble positions

API
---
- Adjusted the logic inside ``Military::removeFromSquad`` to more closely match the game's own behavior


DFHack 52.02-r2
===============

New Features
------------
- `gui/mod-manager`: now supports arena mode

Fixes
-----
- Several fixes related to changes in file system handling in DF 52.01
- `dig-now`: don't allow UNDIGGABLE stones to be excavated
- `gui/mod-manager`:
    - gracefully handle vanilla mods with different versions from the user's preset
    - hide other versions of loaded mods and unhides them when unloaded

Misc Improvements
-----------------
- `autoclothing`: added a ``clear`` option to unset previously set orders

API
---
- Added GUI focus strings for new_arena: ``/Loading`` and ``/Mods``
- Expanded the partial implementations of ``Military::addToSquad`` and ``Military::removeFromSquad``
- ``Filesystem::getBaseDir`` and ``Filesystem::getInstallDir`` added (and made available in Lua)

Lua
---
- Inserting values into STL containers containing nonprimitive types is now supported


DFHack 52.02-r1
===============

Fixes
-----
- Honor the "portable mode" preference setting for locating save folders. Fixes DFHack cosaves not working in most cases.
- ``embark-anyone``: validate viewscreen before using, avoids a crash


DFHack 52.01-r1
===============

New Features
------------
- `tweak`: ``animaltrap-reuse``: make it so built animal traps automatically unload the vermin they catch into stockpiled animal traps, so that they can be automatically re-baited and reused

Fixes
-----
- fixed references to removed ``unit.curse`` compound
- `gui/gm-unit`: remove reference to ``think_counter``, removed in v51.12
- `gui/journal`: fix typo which caused the table of contents to always be regenerated even when not needed
- `gui/mod-manager`: gracefully handle mods with missing or broken ``info.txt`` files
- `uniform-unstick`: resolve overlap with new buttons in 51.13

Lua
---
- ``widgets.Slider``: new mouse-controlled single-headed slider widget

Structures
----------
- removed fake ``curse`` compound in ``unitst`` to resolve an alignment issue


DFHack 51.13-r1
===============

New Features
------------
- Compatibility with DF 51.13


DFHack 51.12-r1.1
=================

New Features
------------
- Compatibility with Itch release of DF 51.12


DFHack 51.12-r1
===============

New Tools
---------
- `deteriorate`: (reinstated) allow corpses, body parts, food, and/or damaged clothes to rot away
- `modtools/moddable-gods`: (reinstated) create new deities from scratch

New Features
------------
- `gui/blueprint`: now records zone designations
- `gui/design`: add option to draw N-point stars, hollow or filled or inverted, and change the main axis to orient in any direction
- `gui/mod-manager`: when run in a loaded world, shows a list of active mods -- click to export the list to the clipboard for easy sharing or posting
- `gui/spectate`: added "Prefer nicknamed" to the list of options

Fixes
-----
- fixed an overly restrictive type constraint that resulted in some object types being glossed as a boolean when passed as an argument from C++ to Lua
- `createitem`: multiple items should be properly created in stacks again
- `getplants`:
    - will no longer crash when faced with plants with growths that do not drop seeds when processed
    - use updated formula for calculating whether plant growths are ripe
    - fix logic for determining whether plant growths have been picked
- `gui/design`: prevent line thickness from extending outside the map boundary
- `gui/teleport`: adapt to new behavior in DF 51.11 to avoid a crash when teleporting items into mid-air
- `plants`: will no longer generate a traceback when a filter is used
- `preserve-rooms`: don't warn when a room is assigned to a non-existent unit.  this is now common behavior for DF when it keeps a room for an unloaded unit
- `script-manager`: fix lua scripts in mods not being reloaded properly upon entering a saved world on Windows
- `starvingdead`:
    - properly restore to correct enabled state when loading a new game that is different from the first game loaded in this session
    - ensure undead decay does not happen faster than the declared decay rate when saving and loading the game

Misc Improvements
-----------------
- All places where units are listed in DFHack tools now show the translated English name in addition to the native name. In particular, this makes units searchable by English name in `gui/sitemap`.
- `blueprint`:
    - support for recording zones
    - support for recording stockpile properties like names and stockpile links; does not yet support recording detailed contents configuration
- `dig`: ASCII overlay now displays priority of digging designations
- `remove-stress`: also applied to long-term stress, immediately removing stressed and haggard statuses
- `spectate`: added prefer nicknamed units
- `strangemood`: support added for specifying unit id instead of selected unit or random one.

Removed
-------
- removed historically unused ``Core::RegisterData``/``Core::GetData`` API and associated internal data structures

API
---
- ``cuboid::forCoord``, ``Maps::forCoord``: take additional parameter to control whether iteration goes in column major or row major order
- ``Items::getDescription``: fixed display of quality levels, now displays ALL item designations (in correct order) and obeys vanilla SHOW_IMP_QUALITY setting
- ``Random`` module: added ``SplitmixRNG`` class, implements the Splitmix64 RNG used by Dwarf Fortress for "simple" randomness

Lua
---
- ``script-manager``:
    - new ``get_active_mods()`` function for getting information on active mods
    - new ``get_mod_info_metadata()`` function for getting information out of mod ``info.txt`` files


DFHack 51.11-r1.2
=================

Fixes
-----
- `preserve-tombs`: will no longer crash when a tomb is assigned to a unit that does not exist


DFHack 51.11-r1.1
=================

Fixes
-----
- `gui/design`: fix misaligned shape icons
- `preserve-rooms`: will no longer crash when a civzone is assigned to a unit that does not exist


DFHack 51.11-r1
===============

Fixes
-----
- text widgets no longer lose their cursor when the Ctrl-a (select all) hotkey is pressed when there is no text to select
- `dig-now`:
    - fix cases where boulders/rough gems of incorrect material were being generated when digging through walls
    - properly generate ice boulders when digging through ice walls
- `gui/petitions`: fix date math when determining petition age
- `gui/rename`: fix commandline processing when manually specifying target ids
- `gui/sandbox`: restore metal equipment options when spawning units
- `gui/teleport`: now properly handles teleporting units that are currently falling or being flung
- `list-agreements`: fix date math when determining petition age
- `spectate`: don't show a hover tooltip for hidden units (e.g. invisible snatchers)
- `stockpiles`: fix one-off error in item type when importing furniture stockpile settings
- `suspendmanager`: fix walls being treated as potential suitable access if another wall is built underneath
- `unload`: fix recent regression where `unload` would immediately `reload` the target
- ``Buildings`` module: do not crash if a ``map_block`` unexpectedly contains an item that is not on the master item vector

Misc Improvements
-----------------
- `fix/loyaltycascade`: now also breaks up brawls and other intra-fort conflicts that *look* like loyalty cascades
- `makeown`: remove selected unit from any current conflicts so they don't just start attacking other citizens when you make them a citizen of your fort
- `spectate`: show dwarves' activities (like prayer)

API
---
- ``Buildings::setOwner``: updated for changes in 51.11
- ``Buildings`` module: add ``getOwner`` (using the ``Units::get_cached_unit_by_global_id`` mechanic) to reflect changes in 51.11
- ``Military`` module: added ``addToSquad`` function
- ``Units::teleport``: projectile information is now cleared for teleported units
- ``Units`` module: added ``get_cached_unit_by_global_id`` to emulate how DF handles unit vector index caching (used in civzones and in general references)

Lua
---
- ``dfhack.buildings.getOwner``: make new Buildings API available to Lua
- ``dfhack.military.addToSquad``: expose Military API function


DFHack 51.10-r1
===============

Misc Improvements
-----------------
- Compatibility with DF 51.10


DFHack 51.09-r1
===============

New Features
------------
- `gui/journal`: Ctrl-j hotkey to launch `gui/journal` now works in adventure mode!
- `gui/mass-remove`: add a button to the bottom toolbar when eraser mode is active for launching `gui/mass-remove`
- `gui/sitemap`: add a button to the toolbar at the bottom left corner of the screen for launching `gui/sitemap`
- `idle-crafting`: default to only considering happy and ecstatic units for the highest need threshold

Fixes
-----
- Fix processing error in the overlay that displays unit preferences in the baron selection list
- `gui/journal`: prevent pause/unpause events from leaking through the UI when keys are mashed
- `idle-crafting`: check that units still have crafting needs before creating a job for them

API
---
- ``Filesystem`` module: rewritten to use C++ standard library components, for better portability


DFHack 51.08-r1
===============

Misc Improvements
-----------------
- Compatibility update for DF 51.08


DFHack 51.07-r1
===============

New Tools
---------
- `autocheese`: automatically make cheese using barrels that have accumulated sufficient milk
- `devel/export-map`: export map tile data to a JSON file
- `gui/notes`: UI for adding and managing notes attached to tiles on the map
- `gui/spectate`: interactive UI for configuring `spectate`
- `launch`: (reinstated) new adventurer fighting move: thrash your enemies with a flying suplex
- `putontable`: (reinstated) make an item appear on a table

New Features
------------
- `advtools`: ``advtools.fastcombat`` overlay (enabled by default) allows you to skip combat animations and the announcement "More" button by mashing the movement keys
- `emigration`: ``nobles`` command for sending freeloader barons back to the sites that they rule over
- `gui/journal`: now working in adventure mode -- journal is per-adventurer, so if you unretire an adventurer, you get the same journal
- `gui/sitemap`: is now the official "go to" tool. new global hotkey for fort and adventure mode: Ctrl-G
- `spectate`:
    - can now specify number of seconds (in real time) before switching to follow a new unit
    - new "cinematic-action" mode that dynamically speeds up perspective switches based on intensity of conflict
    - new global keybinding for toggling spectate mode: Ctrl-Shift-S
    - new overlay panel that allows you to cycle through following next/previous units (regardless of whether spectate mode is enabled)
- `stonesense`: stonesense now offsets the view when you are following a unit in DF, to better center the camera on the unit in stonesense
- `toggle-kbd-cursor`: support adventure mode (Alt-k keybinding now toggles Look mode)

Fixes
-----
- Windows console: fix possible hang if the console returns a too-small window width (for any reason)
- `changevein`: fix a crash that could occur when attempting to change a vein into itself
- `createitem`: produced items will now end up at the look cursor position (if it is active)
- `gui/liquids`:
    - don't add liquids to wall tiles
    - using the remove tool with magma selected will no longer create unexpected unpathable tiles
- `hfs-pit`: use correct wall types when making pits with walls
- `idle-crafting`: do not assign crafting jobs to nobles holding meetings (avoids dangling jobs)
- `overlay`: reset draw context between rendering widgets so context changes can't propagate from widget to widget
- `rejuvenate`:
    - update unit portrait and sprite when aging up babies and children
    - recalculate labor assignments for unit when aging up babies and children (so they can start accepting jobs)
- `spectate`: don't allow temporarily modified announcement settings to be written to disk when "auto-unpause" mode is enabled
- `stonesense`:
    - megashots no longer leave stonesense unresponsive
    - items now properly render on top of stockpile indicators
    - minecarts and wheelbarrows are now shown on the correct layer
- `suspendmanager`: in ASCII mode, building planning mode overlay now only displays when viewing the default map, reducing issues with showing through the UI

Misc Improvements
-----------------
- `autobutcher`: treat animals on restraints as unavailable for slaughter
- `colonies`: support adventure mode
- `devel/query`: support adventure mode
- `devel/tree-info`: support adventure mode
- `gui/confirm`: in the delete manager order confirmation dialog, show a description of which order you have selected to delete
- `gui/create-item`: now accepts a ``pos`` argument of where to spawn items
- `gui/design`: only display vanilla dimensions tooltip if the DFHack dimensions tooltip is disabled
- `gui/notify`:
    - moody dwarf notification turns red when they can't reach workshop or items
    - save reminder now appears in adventure mode
    - save reminder changes color to yellow at 30 minutes and to orange at 60 minutes
- `gui/sitemap`: shift click to start following the selected unit or artifact
- `hfs-pit`:
    - improve placement of stairs w/r/t eerie pits and ramp tops
    - support adventure mode
- `hide-tutorials`:
    - handle tutorial popups for adventure mode
    - new ``reset`` command that will re-enable popups in the current game (in case you hid them all and now want them back)
- `modtools/create-item`: exported ``hackWish`` function now supports ``opts.pos`` for determining spawn location
- `position`:
    - add adventurer tile position
    - add global site position
    - when a tile is selected, display relevant map block and intra-block offset
    - report position of the adventure mode look cursor, if active
- `prioritize`:
    - when prioritizing jobs of a specified type, also output how many of those jobs were already prioritized before you ran the command
    - don't include already-prioritized jobs in the output of ``prioritize -j``
- `quickfort`: redesigned ``library/aquifer_tap.cav`` to improve the water fill rate
- `spectate`: player-set configuration is now stored globally instead of per-fort
- `stockpiles`: add property filters for brewable, millable, and processable (e.g. at a Farmer's workshop) organic materials
- `stonesense`: different types of dig-mode designations (normal, autodig, and the blueprint variants of both) now have distinct colors that more closely match the vanilla DF interface

Documentation
-------------
- `stonesense-art-guide`: guide for making sprite art for Stonesense

Removed
-------
- `orders`: MakeCheese job removed from library/basic orders set. Please use `autocheese` instead!
- `stonesense`: removed the "follow DF cursor" tracking mode since the keyboard cursor is no longer commonly used for moving the map around

API
---
- ``Buildings::checkFreeTiles``: now takes a building instead of a pointer to the building extents
- ``Items::getItemBaseValue``: adjust to the reduced value of prepared meals (changed in DF 51.06)
- ``Items::getValue``: magical powers now correctly contribute to item value
- ``Military::removeFromSquad``: removes unit from any squad assignments
- ``Units::isUnitInBox``, ``Units::getUnitsInBox``: don't include inactive units

Lua
---
- ``dfhack.buildings.checkFreeTiles``: now takes a building pointer instead of an extents parameter
- ``dfhack.military.removeFromSquad``: Lua API for ``Military::removeFromSquad``
- ``dfhack.units.setAutomaticProfessions``: sets unit labors according to current work detail settings
- ``gui.dwarfmode``: adventure mode cursor now supported in ``getCursorPos``, ``setCursorPos``, and ``clearCursorPos`` funcitons
- ``overlay.isOverlayEnabled``: new API for querying whether a given overlay is enabled
- ``overlay``: widgets can now declare ``overlay_onenable`` and ``overlay_ondisable`` functions to hook enable/disable

Structures
----------
- create numerous new structures whose contents had previously been missing or inlined into other structures
- fix a variety of structure errors
- merged several duplicate structure/enum types
- promote all bay12 structures, enums, and bitfields to top-level types: this means that most ``T_*`` types now have top-level names
- reorganize all structure definitions to match bay12 header layouts
- specific changes:
    - Building vmethod ``countHospitalSupplies`` now returns ``abstract_building_contents`` instead of ``hospital_supplies``, which has different field names
    - When indexing into a vector named ``scribejobs``, replace ``item_id`` and ``written_content_id`` with ``target_id`` and ``relevant_id``
    - ``conversation_state_type.DenyPermissionSleep`` is now ``SleepPermissionRequested``
    - ``block_square_event_spoorst.[whatever]`` is now ``block_square_event_spoorst.info.[whatever]``
    - ``building_stockpilest.max_*/container_*`` is now ``building_stockpilest.storage.max_*/container_*``
    - ``building_civzonest.zone_settings.pen`` is now ``building_civzonest.zone_settings.pen.flags``
    - ``building_civzonest.zone_settings.tomb`` is now ``building_civzonest.zone_settings.tomb.flags``
    - ``building_bridgest.gate_flags.closed/closing/opening`` are now ``raised/raising/lowering``
    - ``building_weaponst.gate_flags.closed/closing/opening`` are now ``retracted/retracting/unretracting``
    - ``building.design.builder1/builder1_civ/builder2`` are now ``.worker/worker_create_event/curworker`` (and the 2nd is a History Event, not an Entity)
    - ``stockpile_settings.allow_organic/allow_inorganic`` are now ``stockpile_settings.misc.allow_organic/allow_inorganic``
    - ``world.busy_buildings[]`` is now ``world.building_uses.buildings[]``
    - ``world.coin_batches`` is now ``world.coin_batches.all``
    - ``spatter.flags.water_soluble`` is now ``external``
    - ``creation_zone_pwg_alteration_campst.tent_matlgoss`` is now ``.tent_matgloss`` (spelling fix)
    - ``world.raws.body_templates`` and ``world.raws.bodyglosses`` are now ``world.raws.creaturebody.*``
    - ``world.raws.tissue_templates/body_detail_plans/creature_variations`` are now ``world.raws.*.all``
    - ``material_force_adjustst.mat_indx`` is now ``mat_index`` (spelling fix)
    - ``game.minimap.minimap[x][y]`` is now ``game.minimap.minimap[x][y].tile``
    - ``historical_entity.relations.diplomacy[]`` is now ``historical_entity.relations.diplomacy.state[]``
    - ``historical_entity.conquered_site_group_flags`` is now ``historical_entity.law.conquered_site_group_flags``
    - ``world.effects`` is now ``world.effects.all``
    - ``world.raws.entities`` is now ``world.raws.entities.all``
    - ``site_type`` enum deleted, merged with ``world_site_type``
    - ``world.event.dirty_waters[].*`` is now ``world.event.dirty_waters[].pos.*``
    - ``death_condition_type`` enum replaced with ``histfig_body_state`` (notably in ``state_profilest.body_state``)
    - ``history_hit_item``, ``history_event_reason_info``, and ``history_event_circumstance_info`` removed and substituted
    - ``knowledge_profilest.known_locations.ab_review[]`` is now ``.reports[]`` (because ``.known_locations`` got merged with ``site_reputation_info``)
    - ``world.raws.interactions[]`` is now ``world.raws.interactions.all[]``
    - ``itemdef_instrumentst.registers/timbre`` are now ``itemdef_instrumentst.timbre.registers/timbre``
    - ``dye_info`` removed and substituted
    - ``job_art_specification`` removed and substituted
    - ``entity_activity_statistics.discovered_(creature_foods/creatures/plant_foods/plants)`` is now ``entity_activity_statistics.knowledge.*``
    - ``world.mandates[]`` is now ``world.mandates.all[]``
    - ``creature_interaction_effect.counter_trigger.required`` is now ``creature_interaction_effect.counter_trigger.flag.bits.REQUIRED``
    - ``creature_interaction_effect_target`` removed and substituted
    - ``material_common`` removed, its contents prepended to ``material`` and ``material_template``
    - ``world.raws.material_templates`` is now ``world.raws.material_templates.all``
    - ``world.raws.syndromes`` is now ``world.raws.mat_table.syndromes``
    - ``world.raws.effects`` is now ``world.raws.mat_table.effects``
    - ``world.raws.inorganics`` is now ``world.raws.inorganics.all``
    - ``world.raws.inorganics_subset`` is now ``world.raws.inorganics.cheap``
    - ``plotinfo.main.selected_hotkey/in_rename_hotkey`` are now ``plotinfo.main.hotkey_interface.*``
    - ``world.proj_list`` is now ``world.projectiles.all``
    - ``general_ref_building_well_tag.direction`` is now a bitfield
    - ``world_region_details.edges.(split_x/split_y)[][].x/y`` are now ``.break_one/break_two``
    - ``world_population_ref.depth`` is now ``world_population_ref.layer_depth`` and is now an integer instead of an enum
    - Bitfield ``region_weather_flag`` is now ``region_weather_bits`` (to avoid conflicts)
    - Rhythm ``beat_flag`` realigned (``PrimaryAccent`` removed, because it wasn't really a unique flag)
    - ``dipscript_info.script_steps/script_vars`` are now ``dipscript_info.script.steps/vars``
    - ``script_step_discussst.event`` is now ``script_step_discussst.duration``
    - ``script_step_dipeventst`` and ``script_step_invasionst`` fields renamed
    - ``site_architecture_changest.spec_flag`` is now a tagged union
    - ``squad.schedule[x][y]`` is now ``squad.schedule.routine[x].month[y]``
    - ``world.unit_chunks`` is now ``world.unit_chunks.all``
    - ``historical_entity.events[]`` is now ``historical_entity.rumor_info.events``
    - ``world.enemy_status_cache.rel_map[x][y]`` is now ``world.enemy_status_cache.rel_map[x][y].ur``
    - ``unit.curse.interaction_id/interaction_time/interaction_delay/time_on_site/own_interaction/own_interaction_delay`` are now ``unit.curse.interaction.*``
    - ``unit.cached_glowtile_type`` is now ``unit.cache.cached_glowtile_type``
    - ``unit_preference.active`` is now ``unit_preference.flags.visible``
    - ``witness_report_flags`` replaced with correct flags
    - ``caste_body_info.clothing_items.[]`` is now ``caste_body_info.clothing_items.bp[]``
    - ``plant_tree_tile.branches_dir`` enum collapsed into 4 simple flags
    - ``world.populations`` is now ``world.populations.all``
    - ``world_data.constructions.map[x][y][N]`` is now ``world_data.constructions.map[x][y].square[N]``
    - ``world.family_info[]`` is now ``world.family_info.family[]``
    - ``world.fake_world_info[]`` is now ``world.fake_world_info.language[]``
    - ``world.selected_direction`` is now ``world.selected_direction[0]`` (and there are 3 additional entries)


DFHack 51.06-r1
===============

Misc Improvements
-----------------
- Compatibility with DF 51.06


DFHack 51.05-r1
===============

Misc Improvements
-----------------
- Compatibility with DF 51.05


DFHack 51.04-r1.1
=================

New Features
------------
- `stonesense`:
    - added option ``EXTRUDE_TILES`` to slightly expand sprite to avoid gaps (on by default)
    - added option ``PIXELPERFECT_ZOOM`` to change the zoom scale to avoid gaps (off by default)
    - added back minecart track graphics

Fixes
-----
- Ctrl-a hotkeys have been changed to something else (Ctrl-n) for tools that also have an editable text field, where Ctrl-a is interpreted as select all text
- `advtools`: fix dfhack-added conversation options not appearing in the ask whereabouts conversation tree
- `gui/launcher`:
    - ensure commandline is fully visible when searching through history and switching from a very long command to a short command
    - flatten text when pasting multi-line text from the clipboard
- `gui/rename`: fix error when changing the language of a unit's name
- `stonesense`:
    - fixed announcement text rendering off-screen with larger font sizes
    - screen dimensions are now properly set when overriden by a window manager
    - fixed glass cabinets and bookcases being misaligned by 1 pixel
    - fixed unrevealed walls being hidden by default
    - vampires no longer show their true name when they shouldn't
    - fixed debug performance timers to show milliseconds as intended
    - ``CACHE_IMAGES`` now disables mipmapping, stopping sprites from going transparent
    - fixed issue where depth borders wouldn't be rendered for some walls
    - fixed issue where tiles near the bottom edge would be culled

Misc Improvements
-----------------
- `assign-preferences`: new ``--show`` option to display the preferences of the selected unit
- `pref-adjust`: new ``show`` command to display the preferences of the selected unit
- `stonesense`:
    - improved the way altars look
    - fog no longer unnecessarily renders to a separate bitmap
    - added new connective tiles for pools of blood and vomit

Removed
-------
- `gui/control-panel`: removed ``craft-age-wear`` tweak for Windows users; the tweak doesn't currently load on Windows

API
---
- ``Core::getUnpausedMs``: new API for getting unpaused ms since load in a fort-mode game


DFHack 51.04-r1
===============

Misc Improvements
-----------------
- Compatibility with Steam release of DF 51.04


DFHack 51.03-r1.1
=================

Misc Improvements
-----------------
- Compatibility with Itch release of DF 51.03


DFHack 51.03-r1
===============

Fixes
-----
- `gui/gm-editor`: fix Enter key not being recognized for opening the selected object


DFHack 51.02-r1
===============

Fixes
-----
- `deathcause`: fix error when retrieving the name of a historical figure

Misc Improvements
-----------------
- DFHack edit field widgets, such as the commandline editor in `gui/launcher`, now support text selection and other advanced text editing features from `gui/journal`
- `stonesense`:
    - ``keybinds.txt`` config file is now read from ``dfhack-config/stonesense/keybinds.txt``
    - added some missing artwork for bookcases, displays, and offering places
    - reorganized the position of some existing art to be more intuitive
    - added index numbers empty sprite slots to aid in making the xml files for the sprites
    - zoom levels in stonesense now mirror the main game when in follow mode


DFHack 50.15-r2
===============

New Tools
---------
- `fix/stuck-squad`: allow squads and messengers returning from missions to rescue squads that have gotten stuck on the world map
- `gui/rename`: (reinstated) give new in-game language-based names to anything that can be named (units, governments, fortresses, the world, etc.)

New Features
------------
- `gui/notify`: new notification type: save reminder; appears if you have gone more than 15 minutes without saving; click to autosave
- `gui/rename`:
    - add overlay to worldgen screen allowing you to rename the world before the new world is saved
    - add overlay to the "Prepare carefully" embark screen that transparently fixes a DF bug where you can't give units nicknames or custom professions
- `gui/settings-manager`:
    - new overlay on the Labor -> Standing Orders tab for configuring the number of barrels to reserve for job use (so you can brew alcohol and not have all your barrels claimed by stockpiles for container storage)
    - standing orders save/load now includes the reserved barrels setting
- `orders`: add transparent overlays to the manager orders screen that allow right clicks to cancel edit of quantities or condition details instead of exiting to the main screen
- `stockpiles`: add simple import/export dialogs to stockpile overlay panel
- `stonesense`:
    - added hotkey to toggle fog ``;`` (default keybinding)
    - added hotkey to toggle announcements: ``a`` (default keybinding)
    - added hotkey to toggle debug mode: ``~`` (default keybinding)
    - added init file config to show announcements (on by default)
    - added init file config for whether Esc is recognized for closing the stonesense window (on by default to match previous behavior)
    - added init file config for whether creature moods and jobs are displayed (off by default)

Fixes
-----
- `caravan`: no longer incorrectly identify wood-based plant items and plant-based soaps as being ethically unsuitable for trading with the elves
- `fix/dry-buckets`: don't empty buckets for wells that are actively in use
- `gui/design`: don't require an extra right click on the first cancel of building area designations
- `gui/gm-unit`: refresh unit sprite when profession is changed
- `gui/unit-info-viewer`: skill progress bars now show correct XP thresholds for skills past Legendary+5
- `preserve-rooms`:
    - don't erroneously release reservations for units that have returned from their missions but have not yet entered the fort map
    - handle case where unit records are culled by DF immediately after a unit leaves the map
- `preserve-tombs`: properly re-enable after loading a game that had the tool enabled
- `stockpiles`: don't set ``use_links_only`` flag to a random value when the flag is not set to anything in the settings that are being imported
- `stonesense`:
    - fixed crash when maximizing or resizing the window
    - fixed crash when turning the onscreen display (OSD) layer off
- `strangemood`: ensure generated names for artifacts match what the game itself would generate
- `zone`: assign animal to cage/restraint dialog now allows you to unassign a pet from the cage or restraint if the pet is already somehow assigned (e.g.  war dog was in cage and was subsequently assigned to a dwarf)

Misc Improvements
-----------------
- `caravan`: add filter for written works in display furniture assignment dialog
- `dig-now`: handle digging in pool and river tiles
- `fix/wildlife`: don't vaporize stuck wildlife that is onscreen -- kill them instead (as if they died from old age)
- `gui/sitemap`: show primary group affiliation for visitors and invaders (e.g. civilization name or performance troupe)
- `immortal-cravings`: goblins and other naturally non-eating/non-drinking races will now also satisfy their needs for eating and drinking
- `stonesense`:
    - changed announcements to be right-aligned and limited to only show the most recent 10 announcements
    - ``init.txt`` config file is now read from ``dfhack-config/stonesense/init.txt``
    - creature names are now hidden by default (they can still be shown by pressing ``n`` (default keybinding) while stonesense window is active)
    - use smaller increments for zooming in and out
    - OSD is now hidden by default; hit F2 (default keybinding) to show it again
- `strangemood`: add ability to choose Stone Cutting and Stone Carving as the mood skill
- `suspendmanager`: add more specific messages for submerged job sites and those managed by `buildingplan`

Documentation
-------------
- Added example code for creating plugin RPC endpoints that can be used to extend the DFHack API

Removed
-------
- ``dfhack.TranslateName`` has been renamed to ``dfhack.translation.translateName``

API
---
- ``Persistence::getUnsavedSeconds``: returns the number of seconds since last save or load
- ``Translation::generateName``: generates in-game names, mirroring DF's internal logic
- ``Units::getVisibleName``: when acting on a unit without an impersonated identity, returns the unit's name structure instead of the associated histfig's name structure
- ``Units::isUnitInBox``, ``Units::getUnitsInBox``: add versions accepting pos arguments

Internals
---------
- Errors when unloading a plugin's DLL are now checked and reported
- Plugin command callbacks are now called with the core suspended by default so DF memory is always safe to access without extra steps

Lua
---
- ``dfhack.persistent.getUnsavedSeconds``: Lua API for ``Persistence::getUnsavedSeconds``
- ``dfhack.translation.generateName``: Lua API for ``Translation::generateName``
- ``dfhack.units.isUnitInBox``, ``dfhack.units.getUnitsInBox``: add versions accepting pos arguments
- ``widgets.FilteredList``: search keys for list items can now be functions that return a string

Structures
----------
- fixed incorrect vtable address for ``widget`` superclass on Linux


DFHack 50.15-r1.2
=================

Misc Improvements
-----------------
- Updated support for Itch


DFHack 50.15-r1.1
=================

Misc Improvements
-----------------
- Updated support for Classic (Itch not available for analysis yet)


DFHack 50.15-r1
===============

Fixes
-----
- `gui/prerelease-warning`: don't pop up during worldgen, only after a fort has been loaded


DFHack 50.14-r2
===============

New Tools
---------
- `fix/wildlife`: prevent wildlife from getting stuck when trying to exit the map. This fix needs to be enabled manually in `gui/control-panel` on the Bug Fixes tab since not all players want this bug to be fixed (you can intentionally stall wildlife incursions by trapping wildlife in an enclosed area so they are not caged but still cannot escape).
- `forceequip`: (reinstated) forcibly move items into a unit's inventory
- `immortal-cravings`: allow immortals to satisfy their cravings for food and drink
- `infinite-sky`: (reinstated, renamed from ``infiniteSky``) automatically create new z-levels of sky to build in
- `justice`: pardon a criminal's prison sentence

New Features
------------
- `force`: add support for a ``Wildlife`` event to allow additional wildlife to enter the map
- `tweak`: ``realistic-melting``: change melting return for inorganic armor parts, shields, weapons, trap components and tools to stop smelters from creating metal, bring melt return for adamantine in line with other metals to ~95% of forging cost. wear reduces melt return by 10% per level

Fixes
-----
- Fix mouse clicks bleeding through resizable DFHack windows when clicking in the space between the frame and the window content
- `autobutcher`: don't run a scanning and marking cycle on the first tick of a fortress to allow for all custom configuration to be set first
- `control-panel`: fix error when setting numeric preferences from the commandline
- `emigration`: save-and-reload no longer resets the emigration cycle timeout
- `exportlegends`: ensure historical figure race filter is usable after re-entering legends mode with a different loaded world
- `fix/loyaltycascade`: allow the fix to work on non-dwarven citizens
- `geld`, `ungeld`: save-and-reload no longer loses changes done by `geld` and `ungeld` for units who are historical figures
- `gui/notify`: don't classify (peacefully) visiting night creatures as hostile
- `gui/quickfort`:
    - only print a help blueprint's text once even if the repeat setting is enabled
    - fix build mode evaluation rules to allow placement of furniture and constructions on tiles with stair shapes or without orthagonal floors
- `logistics`: don't ignore rotten items when applying stockpile logistics operations (e.g. autodump, autoclaim, etc.)
- `makeown`:
    - quell any active enemy or conflict relationships with converted creatures
    - halt any hostile jobs the unit may be engaged in, like kidnapping
- `nestboxes`: don't consider eggs to be infertile just because the mother has left the nest; eggs can still hatch in this situation
- `rejuvenate`: fix error when specifying ``--age`` parameter
- `timestream`:
    - adjust the incubation counter on fertile eggs so they hatch at the expected time
    - adjust the timeout on traps so they can be re-triggered at normal rates

Misc Improvements
-----------------
- DFHack now verifies that critical DF data structures have known sizes and refuses to start if there is a mismatch
- DFHack text edit fields now delete the character at the cursor when you hit the Delete key
- DFHack text edit fields now move the cursor by one word left or right with Ctrl-Left and Ctrl-Right
- DFHack text edit fields now move the cursor to the beginning or end of the line with Home and End
- Quickfort blueprint library:
    - ``aquifer_tap`` blueprint walkthough rewritten for clarity
    - ``aquifer_tap`` blueprint now designated at priority 3 and marks the stairway tile below the tap in "blueprint" mode to prevent drips while the drainage pipe is being prepared
- `buildingplan`: add value info to item selection dialog (effectively ungrouping items with different values) and add sorting by value
- `fix/occupancy`: additionally handle the case where tile building occupancy needs to be set instead of cleared
- `fix/stuck-worship`: reduced console output by default. Added ``--verbose`` and ``--quiet`` options.
- `gui/design`:
    - add dimensions tooltip to vanilla zone painting interface
    - new ``gui/design.rightclick`` overlay that allows you to cancel out of partially drawn box and minecart designations without canceling completely out of drawing mode
- `gui/gm-editor`: automatically resolve and display names for ``language_name`` fields
- `gui/pathable`: make wagon path to depot representation more robust
- `idle-crafting`: also support making shell crafts for workshops with linked input stockpiles
- `necronomicon`: new ``--world`` option to list all secret-containing items in the entire world
- `orders`: ``orders sort`` now moves orders that are tied to a specific workshop to the top of the list in the global manager orders screen
- `preserve-rooms`: automatically release room reservations for captured squad members. we were kidding ourselves with our optimistic kept reservations. they're unlikely to come back : ((
- `timestream`: improve FPS by a further 10%

Documentation
-------------
- Dreamfort: add link to Dreamfort tutorial youtube series: https://www.youtube.com/playlist?list=PLzXx9JcB9oXxmrtkO1y8ZXzBCFEZrKxve
- The error message that comes up if there is a version mismatch between DF and DFHack now informs you which DF versions are supported by the installed version of DFHack

Removed
-------
- UI focus strings for squad panel flows combined into a single tree: ``dwarfmode/SquadEquipment`` -> ``dwarfmode/Squads/Equipment``, ``dwarfmode/SquadSchedule`` -> ``dwarfmode/Squads/Schedule``
- `faststart`: removed since the vanilla startup sequence is now sufficiently fast
- `modtools/force`: merged into `force`

API
---
- ``DFHack::Units``: new function ``setPathGoal``
- ``Units::setAutomaticProfessions``: bay12-provided entry point to assign labors based on work details

Lua
---
- ``dfhack.units``: new function ``setPathGoal``
- ``widgets.TabBar``: updated to allow for horizontal scrolling of tabs when there are too many to fit in the available space

Structures
----------
- added ``unitst_set_automatic_professions`` entry point export to list of known globals


DFHack 50.14-r1
===============

Fixes
-----
- `autobutcher`: fix regression in ordering of butcherable animals
- `preserve-rooms`: don't reserve a room for citizens that you expel from the fort


DFHack 50.13-r5
===============

New Tools
---------
- `embark-anyone`: allows you to embark as any civilization, including dead and non-dwarven civs
- `gui/family-affairs`: (reinstated) inspect or meddle with pregnancies, marriages, or lover relationships
- `idle-crafting`: allow dwarves to independently satisfy their need to craft objects
- `notes`: attach notes to locations on a fort map
- `preserve-rooms`: manage room assignments for off-map units and noble roles. reserves rooms owned by traveling units and reinstates their ownership when they return to the site. also allows you to assign rooms to noble/administrator roles, and the rooms will be automatically assigned whenever the holder of the role changes

New Features
------------
- `caravan`:
    - DFHack dialogs for trade screens (both ``Bring goods to depot`` and the ``Trade`` barter screen) can now filter by item origins (foreign vs. fort-made) and can filter bins by whether they have a mix of ethically acceptable and unacceptable items in them
    - If you have managed to select an item that is ethically unacceptable to the merchant, an "Ethics warning" badge will now appear next to the "Trade" button. Clicking on the badge will show you which items that you have selected are problematic. The dialog has a button that you can click to deselect the problematic items in the trade list.
- `confirm`: If you have ethically unacceptable items selected for trade, the "Are you sure you want to trade" confirmation will warn you about them
- `exportlegends`: option to filter by race on historical figures page
- `quickfort`: ``#zone`` blueprints now integrated with `preserve-rooms` so you can create a zone and automatically assign it to a noble or administrative role

Fixes
-----
- DFHack screens that allow keyboard cursor and camera movement while focused now also allow diagonal and Z-change keyboard cursor keys
- DFHack state for a site is now properly saved when retiring a fort
- prevent hang when buildings in zones are destroyed in the case where the buildings were not added to the zone in the same order that they were created (uncommon)
- System clipboard: when pasting single lines from the system clipboard, replace newlines with spaces so they don't show up as strange CP437 glyphs in-game
- `buildingplan`:
    - improved performance in forts with large numbers of items
    - fixed processing errors when using quick material filter slot '0'
- `deep-embark`:
    - fix error when embarking where there is no land to stand on (e.g. when embarking in the ocean with `gui/embark-anywhere`)
    - fix failure to transport units and items when embarking where there is no room to spawn the starting wagon
- `empty-bin`: ``--liquids`` option now correctly empties containers filled with LIQUID_MISC (like lye)
- `exterminate`: don't kill friendly undead (unless ``--include-friendly`` is passed) when specifying ``undead`` as the target
- `gui/create-item`, `modtools/create-item`: items of type "VERMIN", "PET", "REMANS", "FISH", "RAW FISH", and "EGG" no longer spawn creature item "nothing" and will now stack correctly
- `gui/design`: don't overcount "affected tiles" for Line & Freeform drawing tools
- `gui/pathable`:
    - fix hang when showing trade depot wagon access and a trade depot is submerged under water or magma
    - fix representation of wagon paths over stairs and through doors
- `gui/settings-manager`: work details overlay no longer disappears when you click on a unit in the unit list
- `gui/teleport`: fix issue when teleporting units that are not prone, resulting in later issues with phantom "cannot build here: unit blocking tile" messages
- `regrass`:
    - no longer add all compatible grass types when using ``--force`` without ``--new``
    - ``--mud`` now converts muddy slade to grass, consistent with normal DF behavior
- `rejuvenate`:
    - don't set a lifespan limit for creatures that are immortal (e.g. elves, goblins)
    - properly disconnect babies from mothers when aging babies up to adults
- `strangemood`: manually-triggered Macabre moods will now correctly request up to 3 bones/remains for the primary component instead of only 1
- `timestream`: ensure child growth events (that is, a child's transition to adulthood) are not skipped; existing "overage" children will be automatically fixed within a year

Misc Improvements
-----------------
- Dreamfort:
    - integrate with `preserve-rooms` to assign relevant rooms to nobles/adimistrators
    - smooth tiles under statues and other large furniture that you can't easily smooth later
- `assign-minecarts`: reassign vehicles to routes where the vehicle has been destroyed (or has otherwise gone missing)
- `buildingplan`: only consider building materials that can be accessed by at least one citizen/resident
- `exterminate`:
    - show descriptive names for the listed races in addition to their IDs
    - show actual names for unique creatures such as forgotten beasts and titans
- `fix/dry-buckets`: prompt DF to recheck requests for aid (e.g. "bring water" jobs) when a bucket is unclogged and becomes available for use
- `fix/ownership`: now also checks and fixes room ownership links
- `gui/control-panel`: include option for turning off dumping of old clothes for `tailor`, for players who have magma pit dumps and want to save old clothes from being dumped into the magma
- `gui/family-affairs`: you can start this tool by the name ``gui/pregnancy`` to start directly on the "Pregnancies" tab
- `gui/sitemap`:
    - show whether a unit is friendly, hostile, or wild
    - show whether a unit is caged
- `position`:
    - report current historical era (e.g., "Age of Myth"), site/adventurer world coords, and mouse map tile coords
    - option to copy keyboard cursor position to the clipboard
- `sort`: can now search for stockpiles on the Places>Stockpile tab by name, number, or enabled item categories

Documentation
-------------
- add documentation for ``dfhack.items.findType(string)`` and ``dfhack.items.findSubtype(string)``
- `gui/embark-anywhere`: add information about how the game determines world tile pathability and instructions for bridging two landmasses
- `modding-guide`:
    - added examples for reading and writing various types of persistent storage
    - updated all code snippets for greater clarity

Removed
-------
- ``quickfortress.csv``: remove old sample blueprints for "The Quick Fortress", which were unmaintained and non-functional in DF v50+. Online blueprints are available at https://docs.google.com/spreadsheets/d/1WuLYZBM6S2nt-XsPS30kpDnngpOQCuIdlw4zjrcITdY if anyone is interested in giving these blueprints some love

API
---
- ``DFHack::cuboid``: ``cuboid::clampMap`` now returns the cuboid itself (instead of boolean) to allow method chaining; call ``cuboid::isValid`` to determine success
- ``Items::createItem``: removed ``growth_print`` parameter; now determined automatically
- ``Units``: new ``isWildlife`` and ``isAgitated`` property checks

Lua
---
- Overlay widgets can now assume their ``active`` and ``visible`` functions will only execute in a context that matches their ``viewscreens`` associations
- ``dfhack.items.createItem``: removed ``growth_print`` parameter to match C++ API
- ``dfhack.units.isDanger``: no longer unconditionally returns true for intelligent undead
- ``dfhack.units``: ``isWildlife`` and ``isAgitated`` property checks
- ``gui.simulateInput``: do not generate spurious keycode from ``_STRING`` key inputs


DFHack 50.13-r4
===============

New Features
------------
- `gui/journal`:
    - new hotkey, accessible from anywhere in fort mode: Ctrl-j
    - new automatic table of contents. add lines that start with "# ", like "# Entry for 502-04-02", to add hyperlinked headers to the table of contents

Fixes
-----
- Copy/Paste: Fix handling of multi-line text when interacting with the system clipboard on Windows
- `add-spatter`: fix a crash related to unloading a savegame with add-spatter reactions, then loading a second savegame with add-spatter reactions
- `autodump`: cancel any jobs that point to dumped items
- `build-now`: fix error when building buildings that (in previous DF versions) required the architecture labor
- `changelayer`: fix incorrect lookup of geological region in multi-region embarks
- `fix/dead-units`: fix error when removing dead units from burrows and the unit with the greatest ID was dead
- `full-heal`: fix ``-r --all_citizens`` option combination not resurrecting citizens
- `gui/autodump`:
    - prevent dumping into walls or invalid map areas
    - properly turn items into projectiles when they are teleported into mid-air
- `gui/settings-manager`: fix position of "settings restored" message on embark when the player has no saved embark profiles
- `gui/unit-info-viewer`: correctly display skill levels when rust is involved
- `list-waves`: no longer gets confused by units that leave the map and then return (e.g. squads who go out on raids)
- `locate-ore`: fix sometimes selecting an incorrect tile when there are multiple mineral veins in a single map block
- `makeown`: ensure names given to adopted units (or units created with `gui/sandbox`) are respected later in legends mode
- `open-legends`: don't intercept text bound for vanilla legends mode search widgets
- `plant`: properly detect trees in a specified cuboid that only have branches/leaves in the cuboid area
- `prioritize`: fix incorrect restoring of saved settings on Windows
- `timestream`:
    - fix dwarves spending too long eating and drinking
    - fix jobs not being created at a sufficient rate, leading to dwarves standing around doing nothing
- `zone`: fix alignment of animal actions overlay panel (the one where you can click to geld/train/etc.) when the animal has a custom portrait (like named dragons)

Misc Improvements
-----------------
- performance improvements for DFHack tools and infrastructure
- `allneeds`: display distribution of needs by how severely they are affecting the dwarf
- `autodump`: allow dumping items into mid-air, converting them into projectiles like `gui/autodump` does
- `build-now`: if `suspendmanager` is running, run an unsuspend cycle immediately before scanning for buildings to build
- `gui/pathable`: give edge tiles where wagons can enter the map a special highlight to make them more identifiable. this is especially useful when the game decides that only a portion of the map edge is usable by wagons.
- `list-waves`:
    - now outputs the names of the dwarves in each migration wave
    - can now display information about specific migration waves (e.g. ``list-waves 0`` to identify your starting 7 dwarves)

Documentation
-------------
- improved docs for ``dfhack.units`` module functions

Removed
-------
- The ``PRELOAD_LIB`` environment variable has been renamed to ``DF_PRELOAD`` to match the naming scheme of other environment variables used by the ``dfhack`` startup script. If you are preloading libraries (e.g. for performance testing) please define ``DF_PRELOAD`` instead of ``PRELOAD_LIB`` or ``LD_PRELOAD``
- ``cuboid::clamp(bool block)``: renamed to ``cuboid::clampMap(bool block)``, name taken by ``cuboid::clamp(cuboid other)``
- ``Units::getPhysicalDescription``: function requires DF call point that is no longer available. alternative is to navigate the unit info sheet and extract the description from the UI (see `markdown`)
- ``Units::MAX_COLORS``, ``Units::findIndexById``, ``Units::getNumUnits``, ``Units::getUnit``: replaced by ``DFHack::COLOR_MAX`` and the generated type-specific ``get_vector`` functions

API
---
- ``cuboid``:
    - construct from ``df::map_block*``, ``forBlock`` iterator to access map blocks in cuboid
    - ``clamp(cuboid other)``, ``clampNew(cuboid other)`` for cuboid intersection. ``clampNew`` returns new cuboid instead of modifying.
- ``Items``: no longer need to pass MapCache parameter to ``moveToGround``, ``moveToContainer``, ``moveToBuilding``, ``moveToInventory``, ``makeProjectile``, or ``remove``
- ``setAreaAquifer``, ``removeAreaAquifer``: add overloads that take cuboid range specifiers
- ``Units::getCasteRaw``: get a caste_raw from a unit or race and caste
- ``Units::getProfessionName``: bool ``land_title`` to append "of Sitename" where applicable, use Prisoner/Slave and noble spouse titles (controlled by ``ignore_noble``)
- ``Units::getProfession``: account for units with fake identities
- ``Units::getRaceChildName``, ``getRaceChildNameById``, ``getRaceBabyName``, ``getRaceBabyNameById``: bool ``plural`` to get plural form
- ``Units::getReadableName``: correct display of ghost+curse names w/r/t each other and unit prof, use ``curse.name`` instead of iterating syndrome name effects
- ``Units::isDanger``: added bool ``hiding_curse``, passed to ``isUndead`` to avoid spoilers
- ``Units::isNaked``: now only checks equipped items (including rings, for now). Setting bool ``no_items`` to true checks empty inventory like before.
- ``Units::isUndead``: bool ``include_vamps`` renamed to ``hiding_curse``. Fn now checks that instead of bloodsucker syndrome.
- ``Units::isUnitInBox``, ``getUnitsInBox``: add versions that take a cuboid range, add filter fn parameter for ``getUnitsInBox``
- ``Units::isVisible``: account for units in cages
- ``Units``: add overloads that take historical figures for ``getReadableName``, ``getVisibleName``, and ``getProfessionName``

Lua
---
- ``dfhack.items.moveToInventory``: make ``use_mode`` and ``body_part`` args optional
- ``dfhack.units``:
    - allow historical figures to be passed instead of units for ``getReadableName``, ``getVisibleName``, and ``getProfessionName``
    - add ``getRaceReadableName``, ``getRaceReadableNameById``, ``getRaceNamePluralById``
- ``gui.ZScreen``: new ``defocused`` property for starting screens without keyboard focus

Structures
----------
- ``world_site``: rename ``is_mountain_halls`` and ``is_fortress`` to Bay12 names ``min_depth`` and ``max_depth``


DFHack 50.13-r3
===============

New Tools
---------
- `advtools`:
    - collection of useful commands and overlays for adventure mode
    - added an overlay that automatically fixes corrupt throwing/shooting state, preventing save/load crashes
    - advtools party - promotes one of your companions to become a controllable adventurer
    - advtools pets - fixes pets you gift in adventure mode.
- `bodyswap`: (reinstated) take control of another unit in adventure mode
- `devel/luacov`: (reinstated) add Lua script coverage reporting for use in testing and performance analysis
- `devel/tree-info`: print a technical visualization of tree data
- `fix/occupancy`: fixes issues where you can't build somewhere because the game tells you an item/unit/building is in the way but there's nothing there
- `fix/population-cap`: fixes the situation where you continue to get migrant waves even when you are above your configured population cap
- `fix/sleepers`: (reinstated) fixes sleeping units belonging to a camp that never wake up.
- `gui/journal`: fort journal with a multi-line text editor
- `gui/sitemap`: list and zoom to people, locations, and artifacts
- `gui/tiletypes`: interface for modifying map tiles and tile properties
- `plant`: (reinstated) tool for creating/growing/removing plants
- `pop-control`: (reinstated) limit the maximum size of migrant waves
- `timestream`: (reinstated) keep the game running quickly even when there are large numbers of units on the map

New Features
------------
- Locale-sensitive number formatting: select your preferred format in `gui/control-panel`. prices and other large numbers in DFHack UIs can be displayed with commas (English formatting), the number formatting used by your system locale, in SI units (e.g. ``12.3k``), or even in scientific notation
- `advtools`: automatically add a conversation option to "ask whereabouts of" for all your relationships (before, you could only ask whereabouts of people involved in rumors)
- `buildingplan`: dimension tooltip is now displayed for constructions and buildings that are designated over an area, like bridges and farm plots
- `gui/design`: all-new visually-driven UI for much improved usability
- `gui/notify`:
    - new notification type: injured citizens; click to zoom to injured units; also displays a warning if your hospital is not functional (or if you have no hospital)
    - new notification type: drowning and suffocation progress bars for adventure mode
- `gui/pathable`: new "Depot" mode that shows whether wagons can path to your trade depot
- `gui/unit-info-viewer`: new overlay for displaying progress bars for skills on the unit info sheet
- `logistics`: automatically forbid or claim items brought to a stockpile
- `plant`: can now ``remove`` shrubs and saplings; ``list`` all valid shrub/sapling raw IDs; ``grow`` can make mature trees older; many new command options
- `prioritize`: new info panel on under-construction buildings showing if the construction job has been taken and by whom. click to zoom to builder; toggle high priority status for job if it's not yet taken and you need it to be built ASAP
- `tweak`: ``named-codices``: display book titles instead of a material description in the stocks/trade screens

Fixes
-----
- Mortal mode: prevent keybindings that run armok tools from being recognized when in mortal mode
- `assign-profile`: fix handling of ``unit`` option for setting target unit id
- `autobutcher`: fix inverted ranking of which animals to butcher first
- `ban-cooking`: ban all seed producing items from being cooked when 'seeds' is chosen instead of just brewable seed producing items
- `buildingplan`: properly identify appropriate construction items for modded buildings built from thread
- `caravan`: fix errors in trade dialog if all fort items are traded away while the trade dialog is showing fort items and the `confirm` trade confirmation is shown
- `clear-smoke`: properly tag smoke flows for garbage collection to avoid memory leak
- `confirm`: fix confirmation prompt behavior when overwriting a hotkey zoom location
- `control-panel`: restore non-default values of per-save enabled/disabled settings for repeat-based commands
- `dig`: don't leave phantom dig designations behind when autodigging warm/damp designated tiles
- `gui/create-item`: allow creation of adamantine thread, wool, and yarn
- `gui/gm-unit`:
    - correctly display skill levels above Legendary+5
    - fix errors when editing/randomizing colors and body appearance
- `gui/notify`: the notification panel no longer responds to the Enter key so Enter key is passed through to the vanilla UI
- `gui/sandbox`:
    - spawned citizens can now be useful military squad members
    - spawned undead now have a purple shade (only after save and reload, though)
- `makeown`: set animals to tame and domesticated
- `overlay`: overlay positions are now adjusted according to the configured max interface width percentage in the DF settings
- `prioritize`: also boost priority of already-claimed jobs when boosting priority of a job type so those jobs are not interrupted
- `quickfort`:
    - fix incorrect handling of stockpiles that are split into multiple separate areas but are given the same label (indicating that they should be part of the same stockpile)
    - allow farm plots to be built on muddy stone (as per vanilla behavior)
- `regrass`: don't remove mud on regrass, consistent with vanilla behavior
- `seedwatch`:
    - display a limit of ``-`` instead of ``0`` for a seed that is present in inventory but not being watched
    - do not include unplantable tree seeds in status report
- `suspend`: remove broken ``--onlyblocking`` option; restore functionality to ``suspend all``
- `tiletypes`: make aquifers functional when adding the ``aquifer`` property and there are no existing aquifer tiles in the same map block
- `warn-stranded`: don't warn for babies carried by mothers who happen to be gathering fruit from trees
- `zone`:
    - animal assignment overlay button moved to not conflict with vanilla aquarium/terrarium button on glass cages
    - allow friendly creatures to be released from cages by assigning them to a pasture zone and then unassigning them
- ``Buildings::containsTile``: fix result for buildings that are solid and have no extent structures
- ``Gui::makeAnnouncement``, ``Gui::autoDFAnnouncement``: fix case where a new announcement is created instead of adding to the count of an existing announcement if the existing announcement was the first one in the reports vector

Misc Improvements
-----------------
- Dreamfort:
    - add a full complement of beds and chests to both barracks
    - redesign guildhall/temple/library level for better accessibility
    - walkthrough documentation refresh
    - add milking/shearing station in surface grazing pasture
    - integrate building prioritization into the blueprints and remove `prioritize` checklist steps
    - add plumbing template for filling cisterns with running water
- `autobutcher`: do not butcher pregnant (or brooding) females
- `autonestbox`: wait until juveniles become adults before they are assigned to nestboxes
- `blueprint`: capture track carving designations in addition to already-carved tracks
- `buildingplan`: add option to ignore items from a specified burrow
- `caravan`:
    - optional overlay to hide vanilla "bring trade goods to depot" button (if you prefer to always use the DFHack version and don't want to accidentally click on the vanilla button). enable ``caravan.movegoods_hider`` in `gui/control-panel` UI Overlays tab to use.
    - bring goods to depot screen now shows (approximate) distance from item to depot
    - remember filter settings for pedestal item assignment dialog
    - add shortcut to the trade request screen for selecting item types by value (e.g. so you can quickly select expensive gems or cheap leather)
- `changevein`: follow veins into adjacent map blocks so you can run the command once instead of once per map block that the vein crosses
- `empty-bin`: select a stockpile, tile, or building to empty all containers in the stockpile, tile, or building
- `exterminate`:
    - add ``all`` target for convenient scorched earth tactics
    - add ``--limit`` option to limit number of exterminated creatures
    - add ``knockout`` and ``traumatize`` method for non-lethal incapacitation
- `gui/civ-alert`: you can now register multiple burrows as civilian alert safe spaces
- `gui/control-panel`: highlight preferences that have been changed from the defaults
- `gui/create-item`: allow right click to cancel out of material dialog submenus
- `gui/design`: circles are more circular (now matches more pleasing shape generated by ``digcircle``)
- `gui/launcher`:
    - "space space to toggle pause" behavior is skipped if the game was paused when `gui/launcher` came up to prevent accidental unpausing
    - refresh default tag filter when mortal mode is toggled in `gui/control-panel` so changes to which tools autocomplete take effect immediately
- `gui/notify`: notification panel extended to apply to adventure mode
- `gui/quickfort`:
    - you can now delete your blueprints from the blueprint load dialog
    - allow farm plots, dirt roads, and paved roads to be designated around partial obstructions without calling it an error, matching vanilla behavior
    - buildings can now be constructed in a "high priority" state, giving them first dibs on `buildingplan` materials and setting their construction jobs to the highest priority
- `gui/unit-info-viewer`:
    - add precise unit size in cc (cubic centimeters) for comparison against the wiki values. you can set your preferred number format for large numbers like this in the preferences of `control-panel` or `gui/control-panel`
    - now displays a unit's weight relative to a similarly-sized well-known creature (dwarves, elephants, or cats)
    - shows a unit's size compared to the average for the unit's race
- `gui/unit-syndromes`: make werecreature syndromes easier to search for
- `item`: option for ignoring uncollected spider webs when you search for "silk"
- `nestboxes`: increase the scanning frequency for fertile eggs to reduce the chance that they get snarfed by eager dwarves
- `orders`: you can now delete your exported orders from the import dialog
- `prioritize`:
    - add ``ButcherAnimal`` to the default prioritization list (``SlaughterAnimal`` was already there, but ``ButcherAnimal`` -- which is different -- was missing)
    - list both unclaimed and total counts for current jobs when the --jobs option is specified
    - boost performance of script by not tracking number of times a job type was prioritized
- `quickfort`:
    - support buildable instruments
    - new ``delete`` command for deleting player-owned blueprints (library and mod-added blueprints cannot be deleted)
    - support enabling `logistics` features for autoforbid and autoclaim on stockpiles
- `regrass`: now accepts numerical IDs for grass raws; ``regrass --list`` replaces ``regrass --plant ""``
- `suspendmanager`: add option to ``unsuspend`` that unsuspends all jobs, regardless of potential issues (like blocking other construction jobs)
- `tiletypes`:
    - performance improvements when affecting tiles over a large area
    - support for creating heavy aquifers
    - new ``autocorrect`` property for autocorrecting adjacent tiles when making changes (e.g. adding ramp tops when you add a ramp)

Documentation
-------------
- Developer's primer for DFHack's type identity system
- `installing`: add instructions for how to use Steam DFHack with non-Steam DF (e.g. to benefit from DFHack auto-updates and cloud backups)
- `modding-guide`: add a section on persistent storage, both for global settings and world-specific settings

Removed
-------
- `adv-fix-sleepers`: renamed to `fix/sleepers`
- `adv-rumors`: merged into `advtools`
- `devel/find-offsets`, `devel/find-twbt`, `devel/prepare-save`: remove development scripts that are no longer useful
- `fix/item-occupancy`, `fix/tile-occupancy`: merged into `fix/occupancy`
- `max-wave`: merged into `pop-control`
- `plants`: renamed to `plant`
- ``dfhack.HIDE_CONSOLE_ON_STARTUP`` and ``dfhack.HIDE_ARMOK_TOOLS`` are no longer directly accessible. Please use `control-panel` or `gui/control-panel` to interact with those settings.
- ``gui.FramedScreen``: this class is now deprecated; please use ``gui.ZScreen`` and ``widgets.Window`` instead

API
---
- Focus strings have moved for stockpile states: ``dwarfmode/CustomStockpile`` is now ``dwarfmode/Stockpile/Some/Customize`` and similar for ``dwarfmode/StockpileTools`` and ``dwarfmode/StockpileLink``
- ``Buildings::getName``: get a building's name
- ``format_number``: format numbers according to the configured player formatting preference
- ``Items::remove``: now cancels related jobs and marks the item as hidden and forbidden until it can be garbage collected
- ``Job::addGeneralRef``: new easy API for creating general references and adding them to a Job
- ``Job::addWorker``: new API function for assigning a job to unit
- ``Maps::isTileAquifer``, ``Maps::isTileHeavyAquifer``, ``Maps::setTileAquifer``, ``Maps::removeTileAquifer``, ``Maps::setAreaAquifer``, ``Maps::removeAreaAquifer``: new aquifer detection and modification API
- ``Units::create``, ``Units::makeown``: new APIs to use bay12-provided entry points for low-level operations

Lua
---
- ``dfhack.formatInt``, ``dfhack.formatFloat``: formats numbers according to the player preferences for number formatting set in `gui/control-panel`
- ``dfhack.gui.getSelectedJob``: can now return the job with a destination under the keyboard cursor (e.g. digging/carving/engraving jobs)
- ``dfhack.internal.getClipboardTextCp437Multiline``: for retrieving multiline text from the system clipboard
- ``dfhack.maps.isTileAquifer``, ``dfhack.maps.isTileHeavyAquifer``, ``dfhack.maps.setTileAquifer``, ``dfhack.maps.removeTileAquifer``: access to new aquifer API
- ``dfhack.units.create``, ``dfhack.units.makeown``: Lua access to new module API
- ``dialogs.showYesNoPrompt``: extend options so the standard dialog can be used for `gui/confirm`-style confirmation prompts
- ``gui.get_interface_rect``, ``gui.get_interface_frame``: convenience functions for working with scaled interfaces
- ``overlay``: new attributes: ``fullscreen`` and ``full_interface`` for overlays that need access to the entire screen or the scaled interface area, respectively
- ``plugins.tiletypes.tiletypes_setTile``: can now accept a table for access to previously unavailable options
- ``safe_index``: will now return nil when attempting to index into a non-indexable object
- ``script-manager``: add ``getModSourcePath`` and ``getModStatePath`` so modders can get the directory path to their own files
- ``string:wrap``: now preserves inter-word spacing and can return the wrapped lines as a table of strings instead of a single multi-line string
- ``widgets.ButtonGroup``: subclass of CycleHotkeyLabel that additionally displays clickable graphical buttons
- ``widgets.CycleHotkeyLabel``: when the widget has both forward and backward hotkeys defined, support moving backwards by clicking on the appropriate hotkey hint
- ``widgets.DimensionsTooltip``: reusable selected dimensions tooltip that follows the mouse cursor around
- ``widgets.FilteredList``: don't restrict the player from inputting multiple successive space characters
- ``widgets.makeButtonLabelText``: create text and graphical buttons from character/color/tile maps and/or dynamically loaded tilesets

Structures
----------
- added several bay12 exported entry points to list of known globals
- canonicalized a wide swath of type names, field names, and structure organization to match DF's internal names and organization. fields that already had useful names were largely left alone, but all ``unk``, ``anon``, and other "placeholder" names have been changed. structures that differed from reality were also corrected (e.g. collections of fields that were actually substructures and vice versa).
- ``job.item_category`` is now ``job.specflag``, contains a union of flag fields, and depends on the job type
- ``plant_flags``: rename ``is_burning``, ``is_drowning``, ``is_dead`` to Bay12 names ``unused_01``, ``season_dead``, ``dead``
- ``slab_engraving_type``: correct order of items (last two were swapped)
- ``unitst``: correct return type of ``create_nemesis`` vmethod
- ``world_data``: identify many fields and substructures


DFHack 50.13-r2.1
=================

Fixes
-----
- `suspendmanager`: stop suspending single tile stair constructions


DFHack 50.13-r2
===============

New Tools
---------
- Updated for adventure mode:
    - `reveal`
    - `gui/sandbox`, `gui/create-item`, `gui/reveal`
- `adaptation`: (reinstated) inspect or set unit cave adaptation levels
- `fix/engravings`: fix corrupt engraving tiles
- `flashstep`: (reinstated) teleport your adventurer to the mouse cursor
- `ghostly`: (reinstated) allow your adventurer to phase through walls
- `markdown`: (reinstated) export description of selected unit or item to a text file
- `resurrect-adv`: (reinstated) allow your adventurer to recover from death
- `reveal-adv-map`: (reinstated) reveal (or hide) the adventure map
- `unretire-anyone`: (reinstated) choose anybody in the world as an adventurer

New Features
------------
- DFHack and the Dwarf Fortress translation project can now both be run at the same time
- `buildingplan`: quick material filter favorites on main planner panel
- `instruments`: new subcommand ``instruments order`` for creating instrument work orders

Fixes
-----
- `blueprint`: correctly define stockpile boundaries in recorded stockpile ("place") blueprints when there are adjacent non-rectangular stockpiles of identical types
- `caravan`: don't include undiscovered divine artifacts in the goods list
- `combine`: respect container volume limits
- `dig`:
    - refresh count of tiles that will be modified by "mark all designated tiles on this z-level for warm/damp dig" when the z-level changes
    - don't affect already-revealed tiles when marking z-level for warm/damp dig
- `gui/quantum`: fix processing when creating a quantum dump instead of a quantum stockpile
- `logistics`: include semi-wild pets when autoretrain is enabled
- `modtools/create-item`: now functions properly when the ``reaction-gloves`` tweak is active
- `prospect`: don't use scientific notation for representing large numbers
- `quickfort`:
    - don't designate multiple tiles of the same tree for chopping when applying a tree chopping blueprint to a multi-tile tree
    - fix detection of valid tiles for wells
- `suspendmanager`: fully suspend unbuildable dead ends (e.g. building second level of a wall when the wall top is only accessible via ramp, causing the planned wall to be pathable but not buildable)
- `zone`:
    - fix display of distance from cage/pit for small pets in assignment dialog
    - refresh values in distance column when switching selected pastures when the assign animals dialog is open

Misc Improvements
-----------------
- Dreamfort: move wells on services level so brawling drunken tavern patrons are less likely to fall in
- New commandline options for controlling the Cloud Save coprocess when launching from Steam. See the `dfhack-core` documentation for details.
- `caravan`: display who is in the cages you are selecting for trade and whether they are hostile
- `combine`: reduce combined drink sizes to 25
- `deathcause`: automatically find and choose a corpse when a pile of mixed items is selected
- `dig`:
    - warm/damp/aquifer status will now be shown in mining mode for tiles that your dwarves can see from the level below
    - warm/damp/aquifer status will now be shown when in smoothing/engraving modes
- `flashstep`: new keybinding for teleporting adventurer to the mouse cursor: Ctrl-t (when adventure map is in the default state and mortal mode is disabled in DFHack preferences)
- `gui/autobutcher`: add shortcuts for butchering/unbutchering all animals
- `gui/launcher`: add button for copying output to the system clipboard
- `gui/quantum`:
    - add option for whether a minecart automatically gets ordered and/or attached
    - when attaching a minecart, show which minecart was attached
    - allow multiple feeder stockpiles to be linked to the minecart route
- `markdown`: new keybinding for triggering text export: Ctrl-t (when unit or item is selected)
- `prioritize`: add PutItemOnDisplay jobs to the default prioritization list -- when these kinds of jobs are requested by the player, they generally want them done ASAP
- `regrass`:
    - can now add grass to stairs, ramps, ashes, buildings, muddy stone, shrubs, and trees
    - can now restrict area of effect to specified tile, block, cuboid, or z-levels
    - can now add grass in map blocks where there hasn't been any
    - can now choose specific grass type
- `stockpiles`: support import and export "desired items" configuration for route stops
- `unretire-anyone`: new keybinding for adding a historical figure to the adventurer selection list in the adventure mode setup screen: Ctrl-a

Documentation
-------------
- Quickfort Blueprint Library: add demo videos for pump stack and light aquifer tap blueprints
- Update docs for dependency requirements and compilation procedures

API
---
- ``dfhack.items.getReadableDescription()``: easy API for getting a human-readable item description with useful annotations and information (like tattered markers or who is in a cage)
- ``Items::createItem``: now returns a list of item pointers rather than a single ID, moved creator parameter to beginning, added growth_print and no_floor parameters at end
- ``World::getAdventurer``: returns current adventurer unit
- ``World::ReadPauseState``: now returns true when the game is effectively paused due to a large panel obscuring the map. this aligns the return value with the visual state of the pause button when in fort mode.

Lua
---
- ``dfhack.internal.setClipboardTextCp437Multiline``: for copying multiline text to the system clipboard
- ``dfhack.items.createItem``: return value and parameters have changed as per C++ API
- ``dfhack.world.getAdventurer``: returns current adventurer unit


DFHack 50.13-r1.1
=================

Fixes
-----
- `deathcause`: fix error on run
- `gui/quantum`: accept all item types in the output stockpile as intended

Documentation
-------------
- Update docs on release procedures and symbol generation


DFHack 50.13-r1
===============

New Tools
---------
- `gui/quantum`: (reinstated) point and click interface for creating quantum stockpiles or quantum dumps
- `gui/unit-info-viewer`: (reinstated) give detailed information on a unit, such as egg laying behavior, body size, birth date, age, and information about their afterlife behavior (if a ghost)

Fixes
-----
- Fixed incorrect DFHack background window texture when DF is started in ascii mode and subsequently switched to graphics mode
- Fixed misidentification of visitors from your own civ as residents; affects all tools that iterate through citizens/residents
- `cursecheck`: act on selected unit only if a unit is selected
- `exterminate`: don't classify dangerous non-invader units as friendly (e.g. snatchers)
- `gui/create-item`:
    - properly restrict bags to bag materials by default
    - allow gloves and shoes to be made out of textiles by default
- `open-legends`: don't interfere with the dragging of vanilla list scrollbars

Misc Improvements
-----------------
- `gui/gm-unit`: changes to unit appearance will now immediately be reflected in the unit portrait
- `open-legends`: allow player to cancel the "DF will now exit" dialog and continue browsing
- `suspendmanager`: Account for walls planned on the z-layer below when determining accessibility to a job

Documentation
-------------
- `autoclothing`: add section comparing ``autoclothing`` and `tailor` to guide players choosing which to enable

Structures
----------
- ``biome_type``: add enum attrs for ``caption`` and ``plant_raw_flags``


DFHack 50.12-r3
===============

New Tools
---------
- `aquifer`: commandline tool for creating, draining, and modifying aquifers
- `gui/aquifer`: interactive aquifer visualization and editing
- `open-legends`: (reinstated) open legends mode directly from a loaded fort

New Features
------------
- `blueprint`:
    - designations and active dig jobs are now captured in generated blueprints
    - warm/damp dig markers are captured in generated blueprints
- `buildingplan`: add overlays for unlinking and freeing mechanisms from buildings
- `dig`:
    - designate tiles for damp or warm dig, which allows you to dig through damp or warm tiles without designations being canceled
    - damp and warm tile icons now remain visible when included in the designation selection box (graphics mode)
    - aquifer tiles are now visually distinct from "just damp" tiles (graphics and ascii modes)
    - light aquifer tiles are now visually distinct from heavy aquifer tiles (graphics and ascii modes)
    - autodig designations that are marked for damp/warm dig propagate the damp/warm tag when expanding to newly exposed tiles
- `gui/notify`: optional notification for general wildlife (not on by default)
- `gui/quickfort`: add options for setting warm/damp dig markers when applying blueprints
- `gui/reveal`: new "aquifer only" mode to only see hidden aquifers but not reveal any tiles
- `quickfort`: add options for setting warm/damp dig markers when applying blueprints

Fixes
-----
- fix behavior of Linux Steam launcher on systems that don't support the inotify API
- fix rendering of resize "notch" in lower right corner of resizable windows in ascii mode
- `agitation-rebalance`: fix calculated percent chance of cavern invasion
- `armoks-blessing`: fix error when making "Normal" attributes legendary
- `emigration`: remove units from burrows when they emigrate
- `fix/loyaltycascade`: fix edge case where loyalties of renegade units were not being fixed
- `gui/launcher`: don't pop up a result dialog if a command run from minimal mode has no output
- `quickfort`:
    - stockpiles can now be placed even if there is water covering the tile, as per vanilla behavior
    - reject tiles for building that contain magma or deep water
- `stonesense`: fix a crash with buildings made of unusual materials (such as campsite tents made out of organic "walls")
- `suspendmanager`: prevent cancellation spam when an item is preventing a building from being completed

Misc Improvements
-----------------
- aquifer_tap blueprint: now designates in damp dig mode for uninterrupted digging in a light aquifer
- pump_stack blueprint: now designates in warm and damp dig mode for uninterrupted digging through warm and damp tiles
- `agitation-rebalance`: when more than the maximum allowed cavern invaders are trying to enter the map, prefer keeping the animal people invaders instead of their war animals
- `gui/control-panel`: add alternate "nodump" version for `cleanowned` that does not cause citizens to toss their old clothes in the dump. this is useful for players who would rather sell old clothes than incinerate them
- `gui/reveal`: show aquifers even when not in mining mode
- `keybinding`: you can now assign keybindings to mouse buttons (if your mouse has more than the three buttons already used by DF)
- `tailor`: allow turning off automatic confiscation of tattered clothing

Documentation
-------------
- Lua API: documented existing ``enum:next_item(index)`` function

Removed
-------
- `drain-aquifer`: replaced by ``aquifer drain --all``; an alias now exists so ``drain-aquifer`` will automatically run the new command

API
---
- ``Buildings::checkFreeTiles``: now takes a ``allow_flow`` parameter to control whether water- or magma-filled tiles are valid
- ``Units::citizensRange``: c++-20 std::range filter for citizen units
- ``Units::forCitizens``: iterator callback function for citizen units
- ``Units::paintTile``, ``Units::readTile``: now takes an optional field specification for reading and writing to specific map compositing layers

Lua
---
- ``dfhack.gui.matchFocusString``: focus string matching is now case sensitive (for performance reasons)

Structures
----------
- name many previously-unknown map-related fields and flag bits
- ``job_type``: new job class type: "Carving" (for smoothing and detailing)
- ``unit_action_data_attack`` (``unit_move_attackst``): identify flags


DFHack 50.12-r2.1
=================

Fixes
-----
- `control-panel`: properly auto-enable newly added bugfixes
- `fix/noexert-exhaustion`: fix typo in control panel registry entry which prevented the fix from being run when enabled
- `gui/suspendmanager`: fix script startup errors
- `orders`: don't intercept keyboard input for setting skill or labor restrictions on workshop workers tab when the player is setting the building nickname

Misc Improvements
-----------------
- `gui/unit-syndromes`: make syndromes searchable by their display names (e.g.  "necromancer")


DFHack 50.12-r2
===============

New Tools
---------
- `agitation-rebalance`: alter mechanics of irritation-related attacks so they are less constant and are more responsive to recent player behavior
- `devel/block-borders`: (reinstated) highlights boundaries of map blocks or embark tile blocks
- `fix/noexert-exhaustion`: fix "Tired" NOEXERT units. Enabling via `gui/control-panel` prevents NOEXERT units from getting stuck in a "Tired" state
- `fix/ownership`: fix instances of multiple citizens claiming the same items, resulting in "Store owned item" job loops
- `fix/stuck-worship`: fix prayer so units don't get stuck in uninterruptible "Worship!" states
- `instruments`: provides information on how to craft the instruments used by the player civilization
- `modtools/if-entity`: (reinstated) modder's resource for triggering scripted content depending on the race of the loaded fort
- `modtools/item-trigger`: (reinstated) modder's resource for triggering scripted content when specific items are used

New Features
------------
- `exterminate`: new "disintegrate" kill method that additionally destroys carried items
- `gui/settings-manager`: add import, export, and autoload for work details
- `logistics`: ``autoretrain`` will automatically assign trainers to your partially-trained (but not yet domesticated) livestock. this prevents children of partially-trained parents from reverting to wild if you don't notice they were born
- `orders`: add overlay for configuring labor and skill level restrictions for workshops
- `quickfort`: allow setting of workshop profile properties (e.g. labor, skill restrictions) from build blueprints
- `sort`: updated and reinstated military status/squad membership/burrow membership filter for work animal assignment screen
- `stocks`: add button/hotkey for removing empty categories from the stocks list

Fixes
-----
- `autochop`: fix underestimation of log yield for cavern mushrooms
- `autoclothing`: don't produce clothes for dead units
- `caravan`: fix trade price calculations when the same item was requested for both import and export
- `catsplosion`: only cause pregnancies in adults
- `control-panel`: fix filtering not filtering when running the ``list`` command
- `gui/launcher`:
    - fix detection on Shift-Enter for running commands and autoclosing the launcher
    - fix history scanning (Up/Down arrow keys) being slow to respond when in minimal mode
- `gui/notify`:
    - prevent notification overlay from showing up in arena mode
    - don't zoom to forbidden depots for merchants ready to trade notification
- `logistics`:
    - don't melt/trade/dump empty containers that happen to be sitting on the stockpile unless the stockpile accepts those item types
    - don't send autotrade items to forbidden depots

Misc Improvements
-----------------
- Dreamfort:
    - the four Craftsdwarf's workshops on the industry level are now specialized for Stonecrafting, Woodcrafting, Bone Carving, and miscellaneous tasks, respectively
    - update embark profile recommendations and example embark profile
- Many tools that previously only worked for citizens or only for dwarves now work for all citizens and residents, e.g. `fastdwarf`, `rejuvenate`, etc.
- When launched from the Steam client on Linux, both Dwarf Fortress and DFHack will be shown as "Running". This ensures that DF has proper accounting for Linux player usage.
- `allneeds`:
    - select a dwarf in the UI to see a summary of needs for just that dwarf
    - provide options for sorting the cumulative needs by different criteria
- `autobutcher`: prefer butchering partially trained animals and save fully domesticated animals to assist in wildlife domestication programs
- `autodump`: can now teleport items loosely stored in buildings (clutter)
- `buildingplan`:
    - remember player preference for whether unavailable materials should be hidden in the filter selection dialog
    - sort by available quantity by default int he filter selection dialog
- `clean`: protect farm plots when cleaning mud
- `control-panel`: enable tweaks quietly on fort load so we don't spam the console
- `devel/tile-browser`: simplify interface now that SDL automatically normalizes texture scale
- `dwarfvet`:
    - automatically unassign animals from pastures when they need treatment so they can make their way to the hospital. reassign them to their original pasture when treatment is complete.
    - ignore animals assigned to cages or restraints
- `exterminate`: make race name matching case and space insensitive
- `gui/gm-editor`: support opening engraved art for inspection
- `gui/launcher`:
    - add interface for browsing and filtering commands by tags
    - add support for history search (Alt-s hotkey) when in minimal mode
    - add support for the ``clear`` command and clearing the scrollback buffer
- `gui/notify`: Shift click or Shift Enter on a zoomable notification to zoom to previous target
- `gui/teleport`: add global Ctrl-Shift-T keybinding (only available when DFHack mortal mode is disabled)
- `prioritize`: print out custom reaction and hauling jobs in the same format that is used for ``prioritize`` command arguments so the player can just copy and paste
- `suspendmanager`: improve performance when there are many active jobs
- `tweak`: add ``quiet`` option for silent enablement and disablement of tweaks

Documentation
-------------
- `introduction`: refresh getting started content
- `overlay-dev-guide`: updated examples and troubleshooting steps
- `quickstart`: refresh quickstart guide

API
---
- ``Units::getCitizens``: now includes residents by default
- ``Units::isForgottenBeast``: property check for forgotten beasts
- ``Units::isGreatDanger``: now includes forgotten beasts
- ``Units::isResident``: property check for residents (as opposed to citizens)

Lua
---
- `helpdb`: ``search_entries`` now returns a match if *all* filters in the ``include`` list are matched. previous behavior was to match if *any* ``include`` filter matched.
- ``dfhack.units.getCitizens``: now includes residents by default
- ``dfhack.units.isForgottenBeast``: make new units method available to Lua
- ``matinfo.decode``: now directly handles plant objects
- ``widgets.Label``: ``*pen`` attributes can now either be a pen or a function that dynamically returns a pen

Structures
----------
- ``activity_event``: identify fields and type values
- ``plant_tree_info``: define tree body and branch flags
- ``plotinfo.hauling``: name fields related to the hauling route panel
- ``unit``: identify and define many previously unknown fields, types, and enums


DFHack 50.12-r1.1
=================

Fixes
-----
- `sort`: fix crash when assigning work animals to units

Removed
-------
- offline HTML rendered docs are no longer distributed with DFHack since they are randomly triggering Windows Defender antivirus heuristics. If you want to download DFHack docs for offline browsing, you can still get them from the Downloads link at https://dfhack.org/docs


DFHack 50.12-r1
===============

Fixes
-----
- `gui/design`: no longer comes up when Ctrl-D is pressed but other DFHack windows have focus
- `gui/notify`: persist notification settings when toggled in the UI

Misc Improvements
-----------------
- `gui/launcher`: developer mode hotkey restored to Ctrl-D
- `sort`: squad assignment overlay rewritten for compatibility with new vanilla data structures and screen layouts

Removed
-------
- `burrow`: removed overlay 3D box select since it is now provided by the vanilla UI
- `sort`: removed Search widgets for screens that now have vanilla search

API
---
- ``Gui::getWidget``: retrieve a vanilla DF widget by name or index

Lua
---
- ``dfhack.gui.getWidgetChildren``: retrieve a list of child widgets for a given widget container
- ``dfhack.gui.getWidget``: retrieve a vanilla DF widget by hierarchy path, with each step specified by a widget name or index


DFHack 50.11-r7
===============

New Tools
---------
- `add-thought`: (reinstated) add custom thoughts to a dwarf
- `combat-harden`: (reinstated) set a dwarf's resistance to being affected by visible corpses
- `devel/input-monitor`: interactive UI for debugging input issues
- `gui/notify`: display important notifications that vanilla doesn't support yet and provide quick zoom links to notification targets.
- `gui/petitions`: (reinstated) show outstanding (or all historical) petition agreements for guildhalls and temples
- `list-waves`: (reinstated) show migration wave information
- `make-legendary`: (reinstated) make a dwarf legendary in specified skills
- `pet-uncapper`: (reinstated, renamed from ``petcapRemover``) allow pets to breed beyond the default population cap of 50
- `tweak`: (reinstated) a collection of small bugfixes and gameplay tweaks
- `undump-buildings`: (reinstated) remove dump designation from in-use building materials

New Features
------------
- `cleanowned`: Add a "nodump" option to allow for confiscating items without dumping
- `tweak`: Add "flask-contents", makes flasks/vials/waterskins be named according to their contents

Fixes
-----
- `autoclothing`: Fix enabled behavior
- `caravan`: display book and scroll titles in the goods and trade dialogs instead of generic scroll descriptions
- `dig-now`: fix digging stairs in the surface sometimes creating underworld gates.
- `dig`: overlay that shows damp designations in ASCII mode now properly highlights tiles that are damp because of an aquifer in the layer above
- `fix/retrieve-units`: prevent pulling in duplicate units from offscreen
- `gui/blueprint`: changed hotkey for setting blueprint origin tile so it doesn't conflict with default map movement keys
- `gui/control-panel`: fix error when toggling autostart settings
- `gui/design`: clicking the center point when there is a design mark behind it will no longer simultaneously enter both mark dragging and center dragging modes. Now you can click once to move the shape, and click twice to move only the mark behind the center point.
- `item`: avoid error when scanning items that have no quality rating (like bars and other construction materials)
- `source`: fix issue where removing sources would make some other sources inactive
- `strangemood`: correctly recognize Stonecutter and Stone Carver as moodable skills, move the Mason's boosted mood chance to the Stone Carver, and select Fell/Macabre based on long-term stress
- `warn-stranded`:
    - don't complain about units that aren't on the map (e.g.  soldiers out on raids)
    - when there was at least one truly stuck unit and miners were actively mining, the miners were also confusingly shown in the stuck units list
- ``gui.View:getMouseFramePos``: function now detects the correct coordinates even when the widget is nested within other frames
- ``Gui::makeAnnouncement``, ``Gui::autoDFAnnouncement``: don't display popup for all announcement types
- ``Gui::revealInDwarfmodeMap``: properly center the zoom even when the target tile is near the edge of the map
- ``Units::getVisibleName``: don't reveal the true identities of units that are impersonating other historical figures

Misc Improvements
-----------------
- `autonestbox`: assign egg layers to the nestbox they have chosen if they have already chosen a nestbox
- `buildingplan`: use closest matching item rather than newest matching item
- `caravan`: move goods to trade depot dialog now allocates more space for the display of the value of very expensive items
- `exportlegends`: make progress increase smoothly over the entire export and increase precision of progress percentage
- `extinguish`: allow selecting units/items/buildings in the UI to target them for extinguishing; keyboard cursor is only required for extinguishing map tiles that cannot be selected any other way
- `gui/autobutcher`: ask for confirmation before zeroing out targets for all races
- `gui/mod-manager`: will automatically unmark the default mod profile from being the default if it fails to load (due to missing or incompatible mods)
- `gui/quickfort`:
    - can now dynamically adjust the dig priority of tiles designated by dig blueprints
    - can now opt to apply dig blueprints in marker mode
- `item`:
    - change syntax so descriptions can be searched for without indicating the ``--description`` option. e.g. it's now ``item count royal`` instead of ``item count --description royal``
    - add ``--verbose`` option to print each item as it is matched
- `probe`: act on the selected building/unit instead of requiring placement of the keyboard cursor for ``bprobe`` and ``cprobe``
- `regrass`: also regrow depleted cavern moss
- `zone`:
    - animal assignment dialog now shows distance to pasture/cage and allows sorting by distance
    - animal assignment dialog shows number of creatures assigned to this pasture/cage/etc.

Removed
-------
- `gui/create-tree`: replaced by `gui/sandbox`
- `gui/manager-quantity`: the vanilla UI can now modify manager order quantities after creation
- `warn-starving`: combined into `gui/notify`
- `warn-stealers`: combined into `gui/notify`

API
---
- Gui focus strings will now include ``dwarfmode/Default`` if the only other panel open is the Squads panel
- Gui module Announcement functions now use DF's new announcement alert system
- ``Gui::addCombatReport``, ``Gui::addCombatReportAuto``: add versions that take ``report *`` instead of report vector index
- ``Gui::MTB_clean``, ``Gui::MTB_parse``, ``Gui::MTB_set_width``: new functions for manipulating ``markup_text_boxst``
- ``Gui::revealInDwarfmodeMap``: unfollow any currently followed units/items so the viewport doesn't just jump back to where it was
- ``toupper_cp437(char)``, ``tolower_cp437(char)``: new ``MiscUtils`` functions, return a char with case changed, respecting CP437
- ``toUpper``, ``toLower``: ``MiscUtils`` functions renamed to ``toUpper_cp437`` and ``toLower_cp437``, CP437 compliant

Lua
---
- Overlay framework now respects ``active`` and ``visible`` widget attributes
- ``dfhack.gui`` announcement functions use default arguments when omitted
- ``dfhack.units.getCitizens`` now only returns units that are on the map
- ``dfhack.upperCp437(string)``, ``dfhack.lowerCp437(string)``: new functions, return string with all chars changed, respecting CP437 code page

Structures
----------
- ``buildings_other``: add correct types for civzone building vectors
- ``job_skill``: correct ``moodable`` property for several professions


DFHack 50.11-r6
===============

New Features
------------
- `zone`: Add overlay for toggling butchering/gelding/adoption/taming options in animal "Overview" tabs

Fixes
-----
- `dig-now`:
    - remove diagonal ramps rendered unusable by digging
    - fix error propagating "light" and "outside" properties to newly exposed tiles when piercing the surface
- `item`: fix missing item categories when using ``--by-type``
- `makeown`: fix error when adopting units that need a historical figure to be created
- `sort`: fix potential crash when switching between certain info tabs
- `suspendmanager`: overlays for suspended building info panels no longer disappear when another window has focus

Misc Improvements
-----------------
- `autonestbox`: don't automatically assign partially trained egg-layers to nestboxes if they don't have an ongoing trainer assigned since they might revert to wild
- `buildingplan`: replace ``[edit filters]`` button in planner overlay with abbreviated filter information
- `reveal`: automatically reset saved map state when a new save is loaded

Removed
-------
- ``nopause``: functionality has moved to `spectate`

API
---
- ``Gui::getAnyJob``: get the job associated with the selected game element (item, unit, workshop, etc.)
- ``Gui::getAnyWorkshopJob``: get the first job associated with the selected workshop
- ``Units::assignTrainer``: assign a trainer to a trainable animal
- ``Units::unassignTrainer``: unassign a trainer from an animal

Lua
---
- ``dfhack.gui.getAnyJob``: expose API to Lua
- ``dfhack.gui.getAnyWorkshopJob``: expose API to Lua
- ``dfhack.units.assignTrainer``: expose API to Lua
- ``dfhack.units.isTamable``: return false for invaders to match vanilla logic
- ``dfhack.units.unassignTrainer``: expose API to Lua

Structures
----------
- ``soundst``: fix alignment


DFHack 50.11-r5
===============

New Tools
---------
- `control-panel`: new commandline interface for control panel functions
- `gui/biomes`: visualize and inspect biome regions on the map
- `gui/embark-anywhere`:
    - new keybinding (active when choosing an embark site): Ctrl-A
    - bypass those pesky warnings and embark anywhere you want to
- `gui/reveal`: temporarily unhide terrain and then automatically hide it again when you're ready to unpause
- `gui/teleport`: mouse-driven interface for selecting and teleporting units
- `item`: perform bulk operations on groups of items.
- `uniform-unstick`: (reinstated) force squad members to drop items that they picked up in the wrong order so they can get everything equipped properly

New Features
------------
- `gui/mass-remove`: new global keybinding: Ctrl-M while on the fort map
- `gui/settings-manager`: save and load embark difficulty settings and standing orders; options for auto-load on new embark
- `sort`: search and sort for the "choose unit to elevate to the barony" screen. units are sorted by the number of item preferences they have and the units are annotated with the items that they have preferences for
- `uniform-unstick`: add overlay to the squad equipment screen to show a equipment conflict report and give you a one-click button to (attempt to) fix
- `zone`: add button to location details page for retiring unused locations

Fixes
-----
- DFHack tabs (e.g. in `gui/control-panel`) are now rendered correctly when there are certain vanilla screen elements behind them
- Dreamfort: fix holes in the "Inside+" burrow on the farming level (burrow autoexpand is interrupted by the pre-dug miasma vents to the surface)
- When passing map movement keys through to the map from DFHack tool windows, also pass fast z movements (shift-scroll by default)
- `ban-cooking`: fix banning creature alcohols resulting in error
- `buildingplan`:
    - when you save a game and load it again, newly planned buildings are now correctly placed in line after existing planned buildings of the same type
    - treat items in wheelbarrows as unavailable, just as vanilla DF does. Make sure the `fix/empty-wheelbarrows` fix is enabled so those items aren't permanently unavailable!
    - show correct number of materials required when laying down areas of constructions and some of those constructions are on invalid tiles
- `caravan`: ensure items are marked for trade when the move trade goods dialog is closed even when they were selected and then the list filters were changed such that the items were no longer actively shown
- `confirm`: properly detect clicks on the remove zone button even when the unit selection screen is also open (e.g. the vanilla assign animal to pasture panel)
- `empty-bin`: now correctly sends ammunition in carried quivers to the tile underneath the unit instead of teleporting them to an invalid (or possibly just far away) location
- `fastdwarf`:
    - prevent units from teleporting to inaccessible areas when in teledwarf mode
    - allow units to meander and satisfy needs when they have no current job and teledwarf mode is enabled
- `getplants`: fix crash when processing mod-added plants with invalid materials
- `gui/design`:
    - fix incorrect highlight when box selecting area in ASCII mode
    - fix incorrect dimensions being shown when you're placing a stockpile, but a start coordinate hasn't been selected yet
- `misery`: fix error when changing the misery factor
- `quickfort`: if a blueprint specifies an up/down stair, but the tile the blueprint is applied to cannot make an up stair (e.g. it has already been dug out), still designate a down stair if possible
- `reveal`: now avoids revealing blocks that contain divine treasures, encased horrors, and deep vein hollows (so the surprise triggers are not triggered prematurely)
- `sort`:
    - fix mouse clicks falling through the squad assignment overlay panel when clicking on the panel but not on a clickable widget
    - fix potential crash when removing jobs directly from the Tasks info screen
- `source`: water and magma sources and sinks now persist with fort across saves and loads
- `stonesense`: fix crash in cleanup code after mega screenshot (Ctrl-F5) completes; however, the mega screenshot will still make stonesense unresponsive. close and open the stonesense window to continue using it.
- `suspendmanager`: correctly handle building collisions with smoothing designations when the building is on the edge of the map
- `warn-stranded`: don't warn for citizens who are only transiently stranded, like those on stepladders gathering plants or digging themselves out of a hole
- ``Maps::getBiomeType``, ``Maps::getBiomeTypeWithRef``: fix identification of tropical oceans

Misc Improvements
-----------------
- Dreamfort: put more chairs adjacent to each other to make the tavern more "social"
- The "PAUSE FORCED" badge will blink briefly to draw attention if the player attempts to unpause when a DFHack tool window requires the game to be paused
- wherever units are listed in DFHack tools, properties like "agitated" or (-trained-) are now shown
- `autochop`: better error output when target burrows are not specified on the commandline
- `autoclothing` : now does not consider worn (x) clothing as usable/available; reduces overproduction when using `tailor` at same time
- `buildingplan`: add option for preventing constructions from being planned on top of existing constructions (e.g. don't build floors on top of floors)
- `burrow`: flood fill now requires an explicit toggle before it is enabled to help prevent accidental flood fills
- `confirm`:
    - updated confirmation dialogs to use clickable widgets and draggable windows
    - added confirmation prompt for right clicking out of the trade agreement screen (so your trade agreement selections aren't lost)
    - added confirmation prompts for irreversible actions on the trade screen
    - added confirmation prompt for deleting a uniform
    - added confirmation prompt for convicting a criminal
    - added confirmation prompt for re-running the embark site finder
    - added confirmation prompt for reassigning or clearing zoom hotkeys
    - added confirmation prompt for exiting the uniform customization page without saving
- `fastdwarf`: now saves its state with the fort
- `fix/stuck-instruments`: now handles instruments that are left in the "in job" state but that don't have any actual jobs associated with them
- `gui/autobutcher`: interface redesigned to better support mouse control
- `gui/control-panel`:
    - reduce frequency for `warn-stranded` check to once every 2 days
    - tools are now organized by type: automation, bugfix, and gameplay
- `gui/launcher`:
    - now persists the most recent 32KB of command output even if you close it and bring it back up
    - make autocomplete case insensitive
- `gui/mass-remove`:
    - can now differentiate planned constructions, stockpiles, and regular buildings
    - can now remove zones
    - can now cancel removal for buildings and constructions
- `gui/quickcmd`: clickable buttons for command add/remove/edit operations
- `orders`: reduce prepared meal target and raise booze target in ``basic`` importable orders in the orders library
- `sort`:
    - add "Toggle all filters" hotkey button to the squad assignment panel
    - rename "Weak mental fortitude" filter to "Dislikes combat", which should be more understandable
- `uniform-unstick`: warn if a unit belongs to a squad from a different site (can happen with migrants from previous forts)
- `warn-stranded`: center the screen on the unit when you select one in the list
- `work-now`: now saves its enabled status with the fort
- `zone`:
    - add include/only/exclude filter for juveniles to the pasture/pit/cage/restraint assignment screen
    - show geld status and custom profession (if set, it's the lower editable line in creature description) in pasture/pit/cage/restraint assignment screen

Documentation
-------------
- DFHack developer's guide updated, with refreshed `architectural-diagrams`
- UTF-8 text in tool docs is now properly displayed in-game in `gui/launcher` (assuming that it can be converted to cp-437)
- `installing`: Add installation instructions for wineskin on Mac
- `modding-guide`: Add examples for script-only and blueprint-only mods that you can upload to DF's Steam Workshop

Removed
-------
- `channel-safely`: (temporarily) removed due to stability issues with the underlying DF API
- ``persist-table``: replaced by new ``dfhack.persistent`` API

API
---
- New plugin API for saving and loading persistent data. See plugins/examples/skeleton.cpp and plugins/examples/persistent_per_save_example.cpp for details
- Plugin ABI (binary interface) version bump! Any external plugins must be recompiled against this version of DFHack source code in order to load.
- ``capitalize_string_words``: new ``MiscUtils`` function, returns string with all words capitalized
- ``Constructions::designateRemove``: no longer designates the non-removable "pseudo" constructions that represent the top of walls
- ``grab_token_string_pos``: new ``MiscUtils`` function, used for parsing tokens
- ``Items``: add item melting logic ``canMelt(item)``, ``markForMelting(item)``, and ``cancelMelting(item)``
- ``Persistence``:
    - persistent keys are now namespaced by an entity_id (e.g. a player fort site ID)
    - data is now stored one file per entity ID (plus one for the global world) in the DF savegame directory
- ``random_index``, ``vector_get_random``: new ``MiscUtils`` functions, for getting a random entry in a vector
- ``Units.isDanger``: now returns true for agitated wildlife
- ``World``:
    - ``GetCurrentSiteId()`` returns the loaded fort site ID (or -1 if no site is loaded)
    - ``IsSiteLoaded()`` check to detect if a site (e.g. a player fort) is active (as opposed to the world or a map)
    - ``AddPersistentData`` and related functions replaced with ``AddPersistentSiteData`` and ``AddPersistentWorldData`` equivalents

Lua
---
- ``dfhack.capitalizeStringWords``: new function, returns string with all words capitalized
- ``dfhack.isSiteLoaded``: returns whether a site (e.g. a player fort) is loaded
- ``dfhack.items``: access to ``canMelt(item)``, ``markForMelting(item)``, and ``cancelMelting(item)`` from ``Items`` module
- ``dfhack.persistent``: new, table-driven API for easier world- and site-associated persistent storage. See the Lua API docs for details.
- ``dfhack.world.getCurrentSite``: returns the ``df.world_site`` instance of the currently loaded fort
- ``widgets.Divider``: linear divider to split an existing frame; configurable T-junction edges and frame style matching

Structures
----------
- ``alert_button_announcement_id``: now int32_t vector (contains report ids)
- ``announcement_alertst``: defined
- ``announcement_alert_type``: enum defined
- ``announcement_type``: added ``alert_type`` enum attribute
- ``feature_init_flags``: more enum values defined
- ``markup_text_boxst``: updated based on information from Bay12
- ``markup_text_linkst``, ``markup_text_wordst``, ``script_environmentst``: defined
- ``occupation``: realigned
- ``plotinfost``: ``unk23c8_flags`` renamed to ``flags``, updated based on information from Bay12
- ``service_orderst``: type defined
- ``service_order_type``: enum defined
- ``soundst``: defined
- ``viewscreen_choose_start_sitest``: fix structure of warning flags -- convert series of bools to a proper bitmask
- ``world_raws``: ``unk_v50_1``, ``unk_v50_2``, ``unk_v50_3`` renamed to ``text_set``, ``music``, ``sound``


DFHack 50.11-r4
===============

New Tools
---------
- `build-now`: (reinstated) instantly complete unsuspended buildings that are ready to be built

Fixes
-----
- RemoteServer: don't shut down the socket prematurely, allowing continuing connections from, for example, dfhack-run
- `buildingplan`: fix choosing the wrong mechanism (or something that isn't a mechanism) when linking a lever and manually choosing a mechanism, but then canceling the selection
- `combine`: prevent stack sizes from growing beyond quantities that you would normally see in vanilla gameplay
- `gui/design`: Center dragging shapes now track the mouse correctly
- `sort`:
    - fix potential crash when exiting and re-entering a creatures subtab with a search active
    - prevent keyboard keys from affecting the UI when search is active and multiple keys are hit at once
- `tailor`: fix corner case where existing stock was being ignored, leading to over-ordering

Misc Improvements
-----------------
- `buildingplan`:
    - save magma safe mechanisms for when magma safety is requested when linking levers and pressure plates to targets
    - when choosing mechanisms for linking levers/pressure plates, filter out unreachable mechanisms
- `caravan`: enable searching within containers in trade screen when in "trade bin with contents" mode
- `sort`: when searching on the Tasks tab, also search the names of the things the task is associated with, such as the name of the stockpile that an item will be stored in


DFHack 50.11-r3
===============

New Tools
---------
- `burrow`: (reinstated) automatically expand burrows as you dig
- `sync-windmills`: synchronize or randomize movement of active windmills
- `trackstop`: (reimplemented) integrated overlay for changing track stop and roller settings after construction

New Features
------------
- `buildingplan`: allow specific mechanisms to be selected when linking levers or pressure plates
- `burrow`: integrated 3d box fill and 2d/3d flood fill extensions for burrow painting mode
- `fix/dead-units`: gained ability to scrub dead units from burrow membership lists
- `gui/design`: show selected dimensions next to the mouse cursor when designating with vanilla tools, for example when painting a burrow or designating digging
- `prospect`: can now give you an estimate of resources from the embark screen. hover the mouse over a potential embark area and run `prospect`.
- `quickfort`: new ``burrow`` blueprint mode for designating or manipulating burrows
- `sort`: military and burrow membership filters for the burrow assignment screen
- `unforbid`: now ignores worn and tattered items by default (X/XX), use -X to bypass

Fixes
-----
- RemoteServer: continue to accept connections as long as the listening socket is valid instead of closing the socket after the first disconnect
- `buildingplan`: overlay and filter editor gui now uses ctrl-d to delete the filter to avoid conflict with increasing the filter's minimum quality (shift-x)
- `caravan`: price of vermin swarms correctly adjusted down. a stack of 10000 bees is worth 10, not 10000
- `emigration`: fix clearing of work details assigned to units that leave the fort
- `gui/unit-syndromes`: show the syndrome names properly in the UI
- `sort`: when filtering out already-established temples in the location assignment screen, also filter out the "No specific deity" option if a non-denominational temple has already been established
- `stockpiles`: hide configure and help buttons when the overlay panel is minimized
- `tailor`: fix crash on Linux where scanned unit is wearing damaged non-clothing (e.g. a crown)

Misc Improvements
-----------------
- `buildingplan`:
    - display how many items are available on the planner panel
    - make it easier to build single-tile staircases of any shape (up, down, or up/down)
- `dreamfort`: Inside+ and Clearcutting burrows now automatically created and managed
- `sort`:
    - allow searching by profession on the squad assignment page
    - add search for places screens
    - add search for work animal assignment screen; allow filtering by military/squad/civilian/burrow
    - on the squad assignment screen, make effectiveness and potential ratings use the same scale so effectiveness is always less than or equal to potential for a given unit. this way you can also tell when units are approaching their maximum potential
    - new overlay on the animal assignment screen that shows how many work animals each visible unit already has assigned to them
- `warn-stranded`: don't warn for units that are temporarily on unwalkable tiles (e.g. as they pass under a waterfall)

Documentation
-------------
- Document the Lua API for the ``dfhack.world`` module

Removed
-------
- `gui/control-panel`:
    - removed always-on system services from the ``System`` tab: `buildingplan`, `confirm`, `logistics`, and `overlay`. The base services should not be turned off by the player. Individual confirmation prompts can be managed via `gui/confirm`, and overlays (including those for `buildingplan` and `logistics`) are managed on the control panel ``Overlays`` tab.
    - removed `autolabor` from the ``Fort`` and ``Autostart`` tabs. The tool does not function correctly with the new labor types, and is causing confusion. You can still enable `autolabor` from the commandline with ``enable autolabor`` if you understand and accept its limitations.

API
---
- ``Buildings::completebuild``: used to link a newly created building into the world
- ``Burrows::setAssignedUnit``: now properly handles inactive burrows
- ``Gui::getMousePos``: now takes an optional ``allow_out_of_bounds`` parameter so coordinates can be returned for mouse positions outside of the game map (i.e. in the blank space around the map)
- ``Gui::revealInDwarfmodeMap``: gained ``highlight`` parameter to control setting the tile highlight on the zoom target
- ``Maps::getWalkableGroup``: get the walkability group of a tile
- ``Units::getReadableName``: now returns the *untranslated* name

Lua
---
- ``dfhack.buildings.completebuild``: expose new module API
- ``dfhack.gui.getMousePos``: support new optional ``allow_out_of_bounds`` parameter
- ``dfhack.gui.revealInDwarfmodeMap``: gained ``highlight`` parameter to control setting the tile highlight on the zoom target
- ``dfhack.maps.getWalkableGroup``: get the walkability group of a tile
- ``gui.FRAME_THIN``: a panel frame suitable for floating tooltips

Structures
----------
- ``burrow``: add new graphics mode texture and color fields
- ``job_item_flags3``: identify additional flags


DFHack 50.11-r2
===============

New Tools
---------
- `add-recipe`: (reinstated) add reactions to your civ (e.g. for high boots if your civ didn't start with the ability to make high boots)
- `burial`: (reinstated) create tomb zones for unzoned coffins
- `fix/corrupt-jobs`: prevents crashes by automatically removing corrupted jobs
- `preserve-tombs`: keep tombs assigned to units when they die
- `spectate`: (reinstated) automatically follow dwarves, cycling among interesting ones

New Scripts
-----------
- `warn-stranded`: new repeatable maintenance script to check for stranded units, similar to `warn-starving`

New Features
------------
- `burial`: new options to configure automatic burial and limit scope to the current z-level
- `drain-aquifer`:
    - gained ability to drain just above or below a certain z-level
    - new option to drain all layers except for the first N aquifer layers, in case you want some aquifer layers but not too many
- `gui/control-panel`: ``drain-aquifer --top 2`` added as an autostart option
- `logistics`: ``automelt`` now optionally supports melting masterworks; click on gear icon on `stockpiles` overlay frame
- `sort`:
    - new search widgets for Info panel tabs, including all "Creatures" subtabs, all "Objects" subtabs, "Tasks", candidate assignment on the "Noble" subtab, and the "Work details" subtab under "Labor"
    - new search and filter widgets for the "Interrogate" and "Convict" screens under "Justice"
    - new search widgets for location selection screen (when you're choosing what kind of guildhall or temple to dedicate)
    - new search widgets for burrow assignment screen and other unit assignment dialogs
    - new search widgets for artifacts on the world/raid screen
    - new search widgets for slab engraving menu; can filter for only units that need a slab to prevent rising as a ghost
- `stocks`: hotkey for collapsing all categories on stocks screen

Fixes
-----
- `buildingplan`:
    - remove bars of ash, coal, and soap as valid building materials to match v50 rules
    - fix incorrect required items being displayed sometimes when switching the planner overlay on and off
- `dwarfvet`: fix invalid job id assigned to ``Rest`` job, which could cause crashes on reload
- `full-heal`: fix removal of corpse after resurrection
- `gui/sandbox`: fix scrollbar moving double distance on click
- `hide-tutorials`: fix the embark tutorial prompt sometimes not being skipped
- `sort`: don't count mercenaries as appointed officials in the squad assignment screen
- `suspendmanager`: fix errors when constructing near the map edge
- `toggle-kbd-cursor`: clear the cursor position when disabling, preventing the game from sometimes jumping the viewport around when cursor keys are hit
- `zone`:
    - races without specific child or baby names will now get generic child/baby names instead of an empty string
    - don't show animal assignment link for cages and restraints linked to dungeon zones (which aren't normally assignable)

Misc Improvements
-----------------
- Help icons added to several complex overlays. clicking the icon runs `gui/launcher` with the help text in the help area
- `buildingplan`:
    - support filtering cages by whether they are occupied
    - show how many items you need to make when planning buildings
- `gui/gm-editor`: for fields with primitive types, change from click to edit to click to select, double-click to edit. this should help prevent accidental modifications to the data and make hotkeys easier to use (since you have to click on a data item to use a hotkey on it)
- `gui/overlay`: filter overlays by current context so there are fewer on the screen at once and you can more easily click on the one you want to reposition
- `orders`: ``recheck`` command now only resets orders that have conditions that can be rechecked
- `overlay`: allow ``overlay_onupdate_max_freq_seconds`` to be dynamically set to 0 for a burst of high-frequency updates
- `prioritize`: refuse to automatically prioritize dig and smooth/carve job types since it can break the DF job scheduler; instead, print a suggestion that the player use specialized units and vanilla designation priorities
- `quickfort`: now allows constructions to be built on top of constructed floors and ramps, just like vanilla. however, to allow blueprints to be safely reapplied to the same area, for example to fill in buildings whose constructions were canceled due to lost items, floors will not be rebuilt on top of floors and ramps will not be rebuilt on top of ramps
- `sort`: added help button for squad assignment search/filter/sort
- `tailor`: now adds to existing orders if possible instead of creating new ones
- `zone`: animals trained for war or hunting are now labeled as such in animal assignment screens

Documentation
-------------
- unavailable tools are no longer listed in the tag indices in the online docs

Removed
-------
- ``FILTER_FULL_TEXT``: moved from ``gui.widgets`` to ``utils``; if your full text search preference is lost, please reset it in `gui/control-panel`

API
---
- added ``Items::getCapacity``, returns the capacity of an item as a container (reverse-engineered), needed for `combine`

Lua
---
- added ``dfhack.items.getCapacity`` to expose the new module API
- added ``GRAY`` color aliases for ``GREY`` colors
- ``utils.search_text``: text search routine (generalized from internal ``widgets.FilteredList`` logic)

Structures
----------
- add new globals: ``translate_name``, ``buildingst_completebuild``
- ``artifact_rumor_locationst``: defined
- ``viewscreen_worldst``: defined types for ``view_mode`` and ``artifacts_arl`` fields
- ``world_view_mode_type``: defined


DFHack 50.11-r1
===============

New Tools
---------
- `startdwarf`: (reinstated) set number of starting dwarves
- `tubefill`: (reinstated) replenishes mined-out adamantine

New Features
------------
- A new searchable, sortable, filterable dialog for selecting items for display on pedestals and display cases
- `startdwarf`: overlay scrollbar so you can scroll through your starting dwarves if they don't all fit on the screen

Fixes
-----
- EventManager: Unit death event no longer misfires on units leaving the map
- `autolabor`: ensure vanilla work details are reinstated when the fort or the plugin is unloaded
- `suspendmanager`: fixed a bug where floor grates, bars, bridges etc. wouldn't be recognised as walkable, leading to unnecessary suspensions in certain cases.
- ``dfhack.TranslateName()``: fixed crash on certain invalid names, which affected `warn-starving`

Misc Improvements
-----------------
- EventManager:
    - guard against potential iterator invalidation if one of the event listeners were to modify the global data structure being iterated over
    - for ``onBuildingCreatedDestroyed`` events, changed firing order of events so destroyed events come before created events
- `devel/inspect-screen`: display total grid size for UI and map layers
- `digtype`:
    - designate only visible tiles by default, and use "auto" dig mode for following veins
    - added options for designating only current z-level, this z-level and above, and this z-level and below
- `hotkeys`:
    - make the DFHack logo brighten on hover in ascii mode to indicate that it is clickable
    - use vertical bars instead of "!" symbols for the DFHack logo in ascii mode to make it easier to read
- `suspendmanager`: now suspends constructions that would cave-in immediately on completion

Lua
---
- mouse key events are now aligned with internal DF semantics: ``_MOUSE_L`` indicates that the left mouse button has just been pressed and ``_MOUSE_L_DOWN`` indicates that the left mouse button is being held down. similarly for ``_MOUSE_R`` and ``_MOUSE_M``. 3rd party scripts may have to adjust.

Structures
----------
- add new global: ``start_dwarf_count``


DFHack 50.10-r1
===============

Fixes
-----
- 'fix/general-strike: fix issue where too many seeds were getting planted in farm plots
- Linux launcher: allow Steam Overlay and game streaming to function
- `autobutcher`: don't ignore semi-wild units when marking units for slaughter

Misc Improvements
-----------------
- 'sort': Improve combat skill scale thresholds


DFHack 50.09-r4
===============

New Features
------------
- `dig`: new overlay for ASCII mode that visualizes designations for smoothing, engraving, carving tracks, and carving fortifications

Fixes
-----
- `buildingplan`: make the construction dimensions readout visible again
- `gui/mod-manager`: don't continue to display overlay after the raws loading progress bar appears
- `seedwatch`: fix a crash when reading data saved by very very old versions of the plugin

Misc Improvements
-----------------
- `autofish`: changed ``--raw`` argument format to allow explicit setting to on or off
- `caravan`: move goods to depot screen can now see/search/trade items inside of barrels and pots
- `gui/launcher`: show tagged tools in the autocomplete list when a tag name is typed
- `sort`:
    - add sort option for training need on squad assignment screen
    - filter mothers with infants, units with weak mental fortitude, and critically injured units on the squad assignment screen
    - display a rating relative to the current sort order next to the visible units on the squad assignment screen

Documentation
-------------
- add instructions for downloading development builds to the ``Installing`` page

API
---
- `overlay`: overlay widgets can now declare a ``version`` attribute. changing the version of a widget will reset its settings to defaults. this is useful when changing the overlay layout and old saved positions will no longer be valid.

Lua
---
- ``argparse.boolean``: convert arguments to lua boolean values.

Structures
----------
- Identified a number of previously anonymous virtual methods in ``itemst``


DFHack 50.09-r3
===============

New Tools
---------
- `devel/scan-vtables`: scan and dump likely vtable addresses (for memory research)
- `hide-interface`: hide the vanilla UI elements for clean screenshots or laid-back fortress observing
- `hide-tutorials`: hide the DF tutorial popups; enable in the System tab of `gui/control-panel`
- `set-orientation`: tinker with romantic inclinations (reinstated from back catalog of tools)

New Features
------------
- `buildingplan`: one-click magma/fire safety filter for planned buildings
- `exportlegends`: new overlay that integrates with the vanilla "Export XML" button. Now you can generate both the vanilla export and the extended data export with a single click!
- `sort`: search, sort, and filter for squad assignment screen
- `zone`: advanced unit assignment screens for cages, restraints, and pits/ponds

Fixes
-----
- Core:
    - reload scripts in mods when a world is unloaded and immediately loaded again
    - fix text getting added to DFHack text entry widgets when Alt- or Ctrl- keys are hit
- `autobutcher`: fix ``ticks`` commandline option incorrectly rejecting positive integers as valid values
- `buildingplan`: ensure selected barrels and buckets are empty (or at least free of lye and milk) as per the requirements of the building
- `caravan`:
    - corrected prices for cages that have units inside of them
    - correct price adjustment values in trade agreement details screen
    - apply both import and export trade agreement price adjustments to items being both bought or sold to align with how vanilla DF calculates prices
    - cancel any active TradeAtDepot jobs if all caravans are instructed to leave
- `emigration`:
    - fix errors loading forts after dwarves assigned to work details or workshops have emigrated
    - fix citizens sometimes "emigrating" to the fortress site
- `fix/retrieve-units`: fix retrieved units sometimes becoming duplicated on the map
- `gui/launcher`, `gui/gm-editor`: recover gracefully when the saved frame position is now offscreen
- `gui/sandbox`: correctly load equipment materials in modded games that categorize non-wood plants as wood
- `orders`: prevent import/export overlay from appearing on the create workorder screen
- `quickfort`: cancel old dig jobs that point to a tile when a new designation is applied to the tile
- `seedwatch`: ignore unplantable tree seeds
- `starvingdead`: ensure sieges end properly when undead siegers starve
- `suspendmanager`:
    - Fix the overlay enabling/disabling `suspendmanager` unexpectedly
    - improve the detection on "T" and "+" shaped high walls
- `tailor`: remove crash caused by clothing items with an invalid ``maker_race``
- ``dialogs.MessageBox``: fix spacing around scrollable text

Misc Improvements
-----------------
- Surround DFHack-specific UI elements with square brackets instead of red-yellow blocks for better readability
- `autobutcher`: don't mark animals for butchering if they are already marked for some kind of training (war, hunt)
- `caravan`: optionally display items within bins in bring goods to depot screen
- `createitem`: support creating items inside of bags
- `devel/lsmem`: added support for filtering by memory addresses and filenames
- `gui/design`: change "auto commit" hotkey from ``c`` to ``Alt-c`` to avoid conflict with the default keybinding for z-level down
- `gui/gm-editor`:
    - hold down shift and right click to exit, regardless of how many substructures deep you are
    - display in the title bar whether the editor window is scanning for live updates
- `gui/liquids`: support removing river sources by converting them into stone floors
- `gui/quickfort`: blueprint details screen can now be closed with Ctrl-D (the same hotkey used to open the details)
- `hotkeys`: don't display DFHack logo in legends mode since it covers up important interface elements. the Ctrl-Shift-C hotkey to bring up the menu and the mouseover hotspot still function, though.
- `quickfort`: linked stockpiles and workshops can now be specified by ID instead of only by name. this is mostly useful when dynamically generating blueprints and applying them via the `quickfort` API
- `sort`: animals are now sortable by race on the assignment screens
- `suspendmanager`: display a different color for jobs suspended by suspendmanager

API
---
- `RemoteFortressReader`: add a ``force_reload`` option to the GetBlockList RPC API to return blocks regardless of whether they have changed since the last request
- ``Gui``: ``getAnyStockpile`` and ``getAnyCivzone`` (along with their ``getSelected`` variants) now work through layers of ZScreens. This means that they will still return valid results even if a DFHack tool window is in the foreground.
- ``Items::getValue()``: remove ``caravan_buying`` parameter since the identity of the selling party doesn't actually affect the item value
- ``Units``: new animal property check functions ``isMarkedForTraining(unit)``, ``isMarkedForTaming(unit)``, ``isMarkedForWarTraining(unit)``, and ``isMarkedForHuntTraining(unit)``

Lua
---
- ``dfhack.gui``: new ``getAnyCivZone`` and ``getAnyStockpile`` functions; also behavior of ``getSelectedCivZone`` and ``getSelectedStockpile`` functions has changes as per the related API notes
- ``dfhack.items.getValue()``: remove ``caravan_buying`` param as per C++ API change
- ``dfhack.screen.readTile()``: now populates extended tile property fields (like ``top_of_text``) in the returned ``Pen`` object
- ``dfhack.units``: new animal property check functions ``isMarkedForTraining(unit)``, ``isMarkedForTaming(unit)``, ``isMarkedForWarTraining(unit)``, and ``isMarkedForHuntTraining(unit)``
- ``new()``: improved error handling so that certain errors that were previously uncatchable (creating objects with members with unknown vtables) are now catchable with ``pcall()``
- ``widgets.BannerPanel``: panel with distinctive border for marking DFHack UI elements on otherwise vanilla screens
- ``widgets.Panel``: new functions to override instead of setting corresponding properties (useful when subclassing instead of just setting attributes): ``onDragBegin``, ``onDragEnd``, ``onResizeBegin``, ``onResizeEnd``

Structures
----------
- Added ``global_table`` global and corresponding ``global_table_entry`` type
- ``help_context_type``: fix typo in enum name: ``EMBARK_TUTORIAL_CHICE`` -> ``EMBARK_TUTORIAL_CHOICE``
- ``plotinfo``: name the fields related to tutorial popups
- ``viewscreen_legendsst``: realign structure
- ``viewscreen_new_arenast``: added (first appeared in 50.06)


DFHack 50.09-r2
===============

New Plugins
-----------
- `3dveins`: reinstated for v50, this plugin replaces vanilla DF's blobby vein generation with veins that flow smoothly and naturally between z-levels
- `dig`: new ``dig.asciiwarmdamp`` overlay that highlights warm and damp tiles when in ASCII mode. there is no effect in graphics mode since the tiles are already highlighted there
- `dwarfvet`: reinstated and updated for v50's new hospital mechanics; allow your animals to have their wounds treated at hospitals
- `zone`: new searchable, sortable, filterable screen for assigning units to pastures

New Scripts
-----------
- `caravan`: new trade screen UI replacements for bringing goods to trade depot and trading
- `fix/empty-wheelbarrows`: new script to empty stuck rocks from all wheelbarrows on the map

Fixes
-----
- Fix extra keys appearing in DFHack text boxes when shift (or any other modifier) is released before the other key you were pressing
- `gui/autodump`: when "include items claimed by jobs" is on, actually cancel the job so the item can be teleported
- `gui/create-item`: when choosing a citizen to create the chosen items, avoid choosing a dead citizen
- `gui/gm-unit`: fix commandline processing when a unit id is specified
- `logistics`:
    - don't autotrain domestic animals brought by invaders (they'll get attacked by friendly creatures as soon as you let them out of their cage)
    - don't bring trade goods to depot if the only caravans present are tribute caravans
    - fix potential crash when removing stockpiles or turning off stockpile features
- `suspendmanager`:
    - take in account already built blocking buildings
    - don't consider tree branches as a suitable access path to a building

Misc Improvements
-----------------
- Dreamfort: give noble suites double-thick walls and add apartment doors
- Suppress DF keyboard events when a DFHack keybinding is matched. This prevents, for example, a backtick from appearing in a textbox as text when you launch `gui/launcher` from the backtick keybinding.
- `autonick`: add more variety to nicknames based on famous literary dwarves
- `gui/unit-syndromes`: make lists searchable
- `logistics`: bring an autotraded bin to the depot if any item inside is tradeable instead of marking all items within the bin as untradeable if any individual item is untradeable
- `quickfort`: blueprint libraries are now moddable -- add a ``blueprints/`` directory to your mod and they'll show up in `quickfort` and `gui/quickfort`!
- `stockpiles`: include exotic pets in the "tameable" filter
- `suspendmanager`: display the suspension reason when viewing a suspended building
- ``widgets.EditField``: DFHack edit fields now support cut/copy/paste with the system clipboard with Ctrl-X/Ctrl-C/Ctrl-V

Documentation
-------------
- `misery`: rewrite the documentation to clarify the actual effects of the plugin

API
---
- ``Items::markForTrade()``, ``Items::isRequestedTradeGood()``, ``Items::getValue``: see Lua notes below
- ``Units::getUnitByNobleRole``, ``Units::getUnitsByNobleRole``: unit lookup API by role

Internals
---------
- Price calculations fixed for many item types

Lua
---
- ``dfhack.items.getValue``: gained optional ``caravan`` and ``caravan_buying`` parameters for prices that take trader races and agreements into account
- ``dfhack.items.isRequestedTradeGood``: discover whether an item is named in a trade agreement with an active caravan
- ``dfhack.items.markForTrade``: mark items for trade
- ``dfhack.units.getUnitByNobleRole``, ``dfhack.units.getUnitsByNobleRole``: unit lookup API by role
- ``widgets.TextButton``: wraps a ``HotkeyLabel`` and decorates it to look more like a button

Structures
----------
- ``build_req_choicest``: realign structure and fix vmethods
- ``squad_orderst``: fix vmethods


DFHack 50.09-r1
===============

Misc Improvements
-----------------
- `caravan`: new overlay for selecting all/none on trade request screen
- `suspendmanager`: don't suspend constructions that are built over open space

Internals
---------
- Core: update SDL interface from SDL1 to SDL2

Structures
----------
- ``tiletype_shape``: changed RAMP_TOP and ENDLESS_PIT to not walkable to reflect how scripts actually need these types to be treated


DFHack 50.08-r4
===============

New Plugins
-----------
- `logistics`: automatically mark and route items or animals that come to monitored stockpiles. options are toggleable on an overlay that comes up when you have a stockpile selected.

Fixes
-----
- `buildingplan`: don't include artifacts when max quality is masterful
- `dig-now`: clear item occupancy flags for channeled tiles that had items on them
- `emigration`: reassign home site for emigrating units so they don't just come right back to the fort
- `gui/create-item`: allow blocks to be made out of wood when using the restrictive filters
- `gui/liquids`: ensure tile temperature is set correctly when painting water or magma
- `gui/quickfort`:
    - allow traffic designations to be applied over buildings
    - protect against meta blueprints recursing infinitely if they include themselves
- `gui/sandbox`: allow creatures that have separate caste-based graphics to be spawned (like ewes/rams)
- `RemoteFortressReader`: fix a crash with engravings with undefined images
- `workorder`: prevent ``autoMilkCreature`` from over-counting milkable animals, which was leading to cancellation spam for the MilkCreature job

Misc Improvements
-----------------
- Blueprint library:
    - dreamfort: full rewrite and update for DF v50
    - pump_stack: updated walkthrough and separated dig and channel steps so boulders can be cleared
    - aquifer_tap: updated walkthrough
- `autonick`: additional nicknames based on burrowing animals, colours, gems, and minerals
- `combine`: reduce max different stacks in containers to 30 to prevent containers from getting overfull
- `dig-now`: can now handle digging obsidian that has been formed from magma and water
- `gui/autodump`: add option to clear the ``trader`` flag from teleported items, allowing you to reclaim items dropped by merchants
- `gui/control-panel`:
    - add some popular startup configuration commands for `autobutcher` and `autofarm`
    - add option for running `fix/blood-del` on new forts (enabled by default)
- `gui/quickfort`:
    - adapt "cursor lock" to mouse controls so it's easier to see the full preview for multi-level blueprints before you apply them
    - only display post-blueprint messages once when repeating the blueprint up or down z-levels
- `gui/sandbox`: when creating citizens, give them names appropriate for their races
- `orders`:
    - only display import/export/sort/clear panel on main orders screen
    - refine order conditions for library orders to reduce cancellation spam
- `prioritize`: add wild animal management tasks and lever pulling to the default list of prioritized job types
- `quickfort`: significant rewrite for DF v50! now handles zones, locations, stockpile configuration, hauling routes, and more
- `stockpiles`: added ``barrels``, ``organic``, ``artifacts``, and ``masterworks`` stockpile presets
- `suspendmanager`:
    - now suspends construction jobs on top of floor designations, protecting the designations from being erased
    - suspend blocking jobs when building high walls or filling corridors
- `workorder`: reduce existing orders for automatic shearing and milking jobs when animals are no longer available

Documentation
-------------
- `blueprint-library-guide`: update Dreamfort screenshots and links, add ``aquifer_tap`` screenshot

Removed
-------
- `gui/automelt`: replaced by an overlay panel that appears when you click on a stockpile

Structures
----------
- ``abstract_building_libraryst``: initialize unknown variables as DF does
- ``misc_trait_type``: realign


DFHack 50.08-r3
===============

Fixes
-----
- Fix crash for some players when they launch DF outside of the Steam client


DFHack 50.08-r2
===============

New Plugins
-----------
- `add-spatter`: (reinstated) allow mods to add poisons and magical effects to weapons
- `changeitem`: (reinstated) change item material, quality, and subtype
- `createitem`: (reinstated) create arbitrary items from the command line
- `deramp`: (reinstated) removes all ramps designated for removal from the map
- `flows`: (reinstated) counts map blocks with flowing liquids
- `lair`: (reinstated) mark the map as a monster lair (this avoids item scatter when the fortress is abandoned)
- `luasocket`: (reinstated) provides a Lua API for accessing network sockets
- `work-now`: (reinstated, renamed from ``workNow``) prevent dwarves from wandering aimlessly with "No job" after completing a task

New Scripts
-----------
- `assign-minecarts`: (reinstated) quickly assign minecarts to hauling routes
- `diplomacy`: view or alter diplomatic relationships
- `exportlegends`: (reinstated) export extended legends information for external browsing
- `fix/stuck-instruments`: fix instruments that are attached to invalid jobs, making them unusable. turn on automatic fixing in `gui/control-panel` in the ``Maintenance`` tab.
- `gui/autodump`: point and click item teleportation and destruction interface (available only if ``armok`` tools are shown)
- `gui/mod-manager`: automatically restore your list of active mods when generating new worlds
- `gui/sandbox`: creation interface for units, trees, and items (available only if ``armok`` tools are shown)
- `light-aquifers-only`: (reinstated) convert heavy aquifers to light
- `modtools/create-item`: (reinstated) commandline and API interface for creating items
- `necronomicon`: search fort for items containing the secrets of life and death

Fixes
-----
- DFHack screen backgrounds now use appropriate tiles in DF Classic
- RemoteServer: fix crash on malformed json in ``dfhack-config/remote-server.json``
- `autolabor`: work detail override warning now only appears on the work details screen
- `deathcause`: fix incorrect weapon sometimes being reported
- `gui/create-item`: allow armor to be made out of leather when using the restrictive filters
- `gui/design`: Fix building and stairs designation
- `quickfort`:
    - properly allow dwarves to smooth, engrave, and carve beneath walkable tiles of buildings
    - fixed detection of tiles where machines are allowed (e.g. water wheels *can* be built on stairs if there is a machine support nearby)
    - fixed rotation of blueprints with carved track tiles
- `RemoteFortressReader`: ensured names are transmitted in UTF-8 instead of CP437

Misc Improvements
-----------------
- Core: new commandline flag/environment var: pass ``--disable-dfhack`` on the Dwarf Fortress commandline or specify ``DFHACK_DISABLE=1`` in the environment to disable DFHack for the current session.
- Dreamfort: improve traffic patterns throughout the fortress
- Settings: recover gracefully when settings files become corrupted (e.g. by DF CTD)
- Window behavior:
    - non-resizable windows now allow dragging by their frame edges by default
    - if you have multiple DFHack tool windows open, scrolling the mouse wheel while over an unfocused window will focus it and raise it to the top
- `autodump`: no longer checks for a keyboard cursor before executing, so ``autodump destroy`` (which doesn't require a cursor) can still function
- `gui/autodump`: fort-mode keybinding: Ctrl-H (when ``armok`` tools are enabled in `gui/control-panel`)
- `gui/blueprint`: recording of stockpile layouts and categories is now supported. note that detailed stockpile configurations will *not* be saved (yet)
- `gui/control-panel`: new preference for whether filters in lists search for substrings in the middle of words (e.g. if set to true, then "ee" will match "steel")
- `gui/create-item`: ask for number of items to spawn by default
- `gui/design`: Improved performance for drawing shapes
- `gui/gm-editor`:
    - when passing the ``--freeze`` option, further ensure that the game is frozen by halting all rendering (other than for DFHack tool windows)
    - Alt-A now enables auto-update mode, where you can watch values change live when the game is unpaused
- `gui/quickfort`:
    - blueprints that designate items for dumping/forbidding/etc. no longer show an error highlight for tiles that have no items on them
    - place (stockpile layout) mode is now supported. note that detailed stockpile configurations were part of query mode and are not yet supported
    - you can now generate manager orders for items required to complete blueprints
- `light-aquifers-only`: now available as a fort Autostart option in `gui/control-panel`. note that it will only appear if "armok" tools are configured to be shown on the Preferences tab.
- `orders`: update orders in library for prepared meals, bins, archer uniforms, and weapons
- `overlay`: add links to the quickstart guide and the control panel on the DF title screen
- `stockpiles`: allow filtering creatures by tameability

Removed
-------
- `orders`: ``library/military_include_artifact_materials`` library file removed since recent research indicates that platinum blunt weapons and silver crossbows are not more effective than standard steel. the alternate military orders file was also causing unneeded confusion.

Internals
---------
- ``dfhack.internal``: added memory analysis functions: ``msizeAddress``, ``getHeapState``, ``heapTakeSnapshot``, ``isAddressInHeap``, ``isAddressActiveInHeap``, ``isAddressUsedAfterFreeInHeap``, ``getAddressSizeInHeap``, and ``getRootAddressOfHeapObject``

Lua
---
- ``ensure_keys``: walks a series of keys, creating new tables for any missing values
- ``gui``: changed frame naming scheme to ``FRAME_X`` rather than ``X_FRAME``, and added aliases for backwards compatibility. (for example ``BOLD_FRAME`` is now called ``FRAME_BOLD``)
- ``overlay.reload()``: has been renamed to ``overlay.rescan()`` so as not to conflict with the global ``reload()`` function. If you are developing an overlay, please take note of the new function name for reloading your overlay during development.

Structures
----------
- Removed ``steam_mod_manager`` and ``game_extra`` globals. Their contents have been merged back into ``game``.
- ``abstract_building_contents``: identify fields and flags related to location item counts
- ``arena_tree``: identify fields related to tree creation
- ``arena_unit``: identify fields related to unit creation
- ``mod_headerst``: rename ``non_vanilla`` flag to ``vanilla`` to reflect its actual usage
- ``profession``: renamed captions ``Cheese Maker`` to ``Cheesemaker``, ``Bee Keeper`` to ``Beekeeper``, and ``Bone Setter`` to ``Bone Doctor``


DFHack 50.08-r1
===============

Fixes
-----
- `autoclothing`: eliminate game lag when there are many inventory items in the fort
- `buildingplan`:
    - fixed size limit calculations for rollers
    - fixed items not being checked for accessibility in the filter and item selection dialogs
- `deteriorate`: ensure remains of enemy dwarves are properly deteriorated
- `dig-now`: properly detect and complete smoothing designations that have been converted into active jobs
- `suspendmanager`: Fix over-aggressive suspension of jobs that could still possibly be done (e.g. jobs that are partially submerged in water)

Misc Improvements
-----------------
- `buildingplan`:
    - planner panel is minimized by default and now remembers minimized state
    - can now filter by gems (for gem windows) and yarn (for ropes in wells)
- `combine`: Now supports ammo, parts, powders, and seeds, and combines into containers
- `deteriorate`: add option to exclude useable parts from deterioration
- `gui/control-panel`:
    - add preference option for hiding the terminal console on startup
    - add preference option for hiding "armok" tools in command lists
- `gui/gm-editor`:
    - press ``g`` to move the map to the currently selected item/unit/building
    - press ``Ctrl-D`` to toggle read-only mode to protect from accidental changes; this state persists across sessions
    - new ``--freeze`` option for ensuring the game doesn't change while you're inspecting it
- `gui/launcher`: DFHack version now shown in the default help text
- `gui/prerelease-warning`: widgets are now clickable
- `overlay`: add the DFHack version string to the DF title screen
- ``Dwarf Therapist``: add a warning to the Labors screen when Dwarf Therapist is active so players know that changes they make to that screen will have no effect. If you're starting a new embark and nobody seems to be doing anything, check your Labors tab for this warning to see if Dwarf Therapist thinks it is in control (even if it's not running).
- ``toggle-kbd-cursor``: add hotkey for toggling the keyboard cursor (Alt-K)
- ``version``: add alias to display the DFHack help (including the version number) so something happens when players try to run "version"

Removed
-------
- `title-version`: replaced by an `overlay` widget

Lua
---
- ``gui.ZScreenModal``: ZScreen subclass for modal dialogs
- ``widgets.CycleHotkeyLabel``: exposed "key_sep" and "option_gap" attributes for improved stylistic control.
- ``widgets.RangeSlider``: new mouse-controlled two-headed slider widget

Structures
----------
- convert ``mod_manager`` fields to pointers


DFHack 50.07-r1
===============

New Plugins
-----------
- `faststart`: speeds up the "Loading..." screen so the Main Menu appears faster

Fixes
-----
- `blueprint`: interpret saplings, shrubs, and twigs as floors instead of walls
- `caravan`: fix trade good list sometimes disappearing when you collapse a bin
- `combine`: fix error processing stockpiles with boundaries that extend outside of the map
- `gui/control-panel`: the config UI for `automelt` is no longer offered when not in fortress mode
- `gui/gm-editor`: no longer nudges last open window when opening a new one
- `hotkeys`: hotkey hints on menu popup will no longer get their last character cut off by the scrollbar
- `prospector`: display both "raw" Z levels and "cooked" elevations
- `stockpiles`:
    - fix crash when importing settings for gems from other worlds
    - allow numbers in saved stockpile filenames
- `warn-starving`: no longer warns for dead units
- ``launchdf``: launch Dwarf Fortress via the Steam client so Steam Workshop is functional

Misc Improvements
-----------------
- Core: hide DFHack terminal console by default when running on Steam Deck
- Mods:
    - scripts in mods that are only in the steam workshop directory are now accessible. this means that a script-only mod that you never mark as "active" when generating a world will still receive automatic updates and be usable from in-game
    - scripts from only the most recent version of an installed mod are added to the script path
    - give active mods a chance to reattach their load hooks when a world is reloaded
- `buildingplan`:
    - items in the item selection dialog should now use the same item quality symbols as the base game
    - hide planner overlay while the DF tutorial is active so that it can detect when you have placed the carpenter's workshop and bed and allow you to finish the tutorial
    - can now filter by cloth and silk materials (for ropes)
    - rearranged elements of ``planneroverlay`` interface
    - rearranged elements of ``itemselection`` interface
- `gui/control-panel`:
    - bugfix services are now enabled by default
    - add `faststart` to the system services
- `gui/gm-editor`:
    - can now jump to material info objects from a mat_type reference with a mat_index using ``i``
    - the key column now auto-fits to the widest key
- `prioritize`: revise and simplify the default list of prioritized jobs -- be sure to tell us if your forts are running noticeably better (or worse!)

Documentation
-------------
- `installing`: updated to include Steam installation instructions

Lua
---
- added two new window borders: ``gui.BOLD_FRAME`` for accented elements and ``gui.INTERIOR_MEDIUM_FRAME`` for a signature-less frame that's thicker than the existing ``gui.INTERIOR_FRAME``

Structures
----------
- correct bit size of tree body data
- identified fields in ``deep_vein_hollow``, ``glowing_barrier``, and ``cursed_tomb`` map events
- identified ``divine_treasure`` and ``encased_horror`` map events


DFHack 50.07-beta2
==================

New Plugins
-----------
- `getplants`: reinstated: designate trees for chopping and shrubs for gathering according to type
- `prospector`: reinstated: get stone, ore, gem, and other tile property counts in fort mode.

New Scripts
-----------
- `fix/general-strike`: fix known causes of the general strike bug (contributed by Putnam)
- `gui/civ-alert`: configure and trigger civilian alerts
- `gui/seedwatch`: GUI config and status panel interface for `seedwatch`

Fixes
-----
- `buildingplan`:
    - filters are now properly applied to planned stairs
    - existing carved up/down stairs are now taken into account when determining which stair shape to construct
    - upright spike traps are now placed extended rather than retracted
    - you can no longer designate constructions on tiles with magma or deep water, mirroring the vanilla restrictions
    - fixed material filters getting lost for planning buildings on save/reload
    - respect building size limits (e.g. roads and bridges cannot be more than 31 tiles in any dimension)
- `caravan`: item list length now correct when expanding and collapsing containers
- `prioritize`: fixed all watched job type names showing as ``nil`` after a game load
- `suspendmanager`:
    - does not suspend non-blocking jobs such as floor bars or bridges anymore
    - fix occasional bad identification of buildingplan jobs
- `tailor`:
    - properly discriminate between dyed and undyed cloth
    - no longer default to using adamantine cloth for producing clothes
    - take queued orders into account when calculating available materials
    - skip units who can't wear clothes
    - identify more available items as available, solving issues with over-production
- `warn-starving`: no longer warns for enemy and neutral units

Misc Improvements
-----------------
- Mods: scripts in mods are now automatically added to the DFHack script path. DFHack recognizes two directories in a mod's folder: ``scripts_modinstalled/`` and ``scripts_modactive/``. ``scripts_modinstalled/`` folders will always be added the script path, regardless of whether the mod is active in a world. ``scripts_modactive/`` folders will only be added to the script path when the mod is active in the current loaded world.
- `automelt`: now allows metal chests to be melted (workaround for DF bug 2493 is no longer needed)
- `buildingplan`:
    - filters and global settings are now ignored when manually choosing items for a building, allowing you to make custom choices independently of the filters that would otherwise be used
    - if `suspendmanager` is running, then planned buildings will be left suspended when their items are all attached. `suspendmanager` will unsuspend them for construction when it is safe to do so.
    - add option for autoselecting the last manually chosen item (like `automaterial` used to do)
- `combine`:
    - you can select a target stockpile in the UI instead of having to use the keyboard cursor
    - added ``--quiet`` option for no output when there are no changes
- `confirm`: adds confirmation for removing burrows via the repaint menu
- `enable`: can now interpret aliases defined with the `alias` command
- `exterminate`: add support for ``vaporize`` kill method for when you don't want to leave a corpse
- `gui/control-panel`:
    - Now detects overlays from scripts named with capital letters
    - added ``combine all`` maintenance option for automatic combining of partial stacks in stockpiles
    - added ``general-strike`` maintenance option for automatic fixing of (at least one cause of) the general strike bug
- `gui/cp437-table`:
    - now has larger key buttons and clickable backspace/submit/cancel buttons, making it fully usable on the Steam Deck and other systems that don't have an accessible keyboard
    - dialog is now fully controllable with the mouse, including highlighting which key you are hovering over and adding a clickable backspace button
- `gui/design`: Now supports placing constructions using 'Building' mode. Inner and Outer tile constructions are configurable. Uses buildingplan filters set up with the regular buildingplan interface.
- `orders`:
    - add minimize button to overlay panel so you can get it out of the way to read long statue descriptions when choosing a subject in the details screen
    - add option to delete exported files from the import dialog
- `stockpiles`:
    - support applying stockpile configurations with fully enabled categories to stockpiles in worlds other than the one where the configuration was exported from
    - support partial application of a saved config based on dynamic filtering (e.g. disable all tallow in a food stockpile, even tallow from world-specific generated creatures)
    - additive and subtractive modes when applying a second stockpile configuration on top of a first
    - write player-exported stockpile configurations to the ``dfhack-config/stockpiles`` folder. If you have any stockpile configs in other directories, please move them to that folder.
    - now includes a library of useful stockpile configs (see docs for details)
- `stripcaged`:
    - added ``--skip-forbidden`` option for greater control over which items are marked for dumping
    - items that are marked for dumping are now automatically unforbidden (unless ``--skip-forbidden`` is set)

Documentation
-------------
- the ``untested`` tag has been renamed to ``unavailable`` to better reflect the status of the remaining unavailable tools. most of the simply "untested" tools have now been tested and marked as working. the remaining tools are known to need development work before they are available again.
- `modding-guide`: guide updated to include information for 3rd party script developers

Removed
-------
- `autounsuspend`: replaced by `suspendmanager`
- `gui/dig`: renamed to `gui/design`

Lua
---
- ``widgets.CycleHotkeyLabel``:
    - options that are bare integers will no longer be interpreted as the pen color in addition to being the label and value
    - option labels and pens can now be functions that return a label or pen
- ``widgets.Label``:
    - tokens can now specify a ``htile`` property to indicate the tile that should be shown when the Label is hovered over with the mouse
    - click handlers no longer get the label itself as the first param to the click handler

Structures
----------
- realigned ``furniture_type`` enum (added BAG)
- realigned ``stockpile_settings`` for new "corpses" vector


DFHack 50.07-beta1
==================

New Scripts
-----------
- `gui/suspendmanager`: graphical configuration interface for `suspendmanager`
- `suspendmanager`: automatic job suspension management (replaces `autounsuspend`)
- `suspend`: suspends building construction jobs

Fixes
-----
- `buildingplan`:
    - items are now attached correctly to screw pumps and other multi-item buildings
    - buildings with different material filters will no longer get "stuck" if one of the filters currently matches no items
- `gui/launcher`: tab characters in command output now appear as a space instead of a code page 437 "blob"
- `quicksave`: now reliably triggers an autosave, even if one has been performed recently
- `showmood` properly count required number of bars and cloth when they aren't the main item for the strange mood

Misc Improvements
-----------------
- `blueprint-library-guide`:
    - library blueprints have moved from ``blueprints`` to ``hack/data/blueprints``
    - player-created blueprints should now go in the ``dfhack-config/blueprints`` folder. please move your existing blueprints from ``blueprints`` to ``dfhack-config/blueprints``. you don't need to move the library blueprints -- those can be safely deleted from the old ``blueprints`` directory.
- `blueprint`: now writes blueprints to the ``dfhack-config/blueprints`` directory
- `buildingplan`:
    - can now filter by clay materials
    - remember choice per building type for whether the player wants to choose specific items
    - you can now attach multiple weapons to spike traps
    - can now filter by whether a slab is engraved
    - add "minimize" button to temporarily get the planner overlay out of the way if you would rather use the vanilla UI for placing the current building
    - add ``buildingplan reset`` command for resetting all filters to defaults
    - rename "Build" button to "Confirm" on the item selection dialog and change the hotkey from "B" to "C"
- `gui/gm-editor`: can now open the selected stockpile if run without parameters
- `quickfort`: now reads player-created blueprints from ``dfhack-config/blueprints/`` instead of the old ``blueprints/`` directory. Be sure to move over your personal blueprints to the new directory!
- `showmood`: clarify how many bars and/or cloth items are actually needed for the mood

Removed
-------
- `buildingplan`: "heat safety" setting is temporarily removed while we investigate incorrect item matching

Structures
----------
- identified two fields related to saves/autosaves to facilitate quicksave implementation


DFHack 50.07-alpha3
===================

Fixes
-----
- `dig-now`: fixed multi-layer channel designations only channeling every second layer
- `gui/create-item`: fix generic corpsepiece spawning
- ``dfhack.job.isSuitableMaterial``: now properly detects lack of fire and magma safety for vulnerable materials with high melting points
- ``widgets.HotkeyLabel``: don't trigger on click if the widget is disabled

Misc Improvements
-----------------
- `buildingplan`: entirely new UI for building placement, item selection, and materials filtering!
- `dig-now`: added handling of dig designations that have been converted into active jobs
- `gui/create-item`: added ability to spawn 'whole' corpsepieces (every layer of a part)
- `gui/dig`:
    - Allow placing an extra point (curve) while still placing the second main point
    - Allow placing n-point shapes, shape rotation/mirroring
    - Allow second bezier point, mirror-mode for freeform shapes, symmetry mode

Removed
-------
- `automaterial`: all functionality has been merged into `buildingplan`
- ``gui.THIN_FRAME``: replaced by ``gui.INTERIOR_FRAME``

API
---
- Gui focus strings will no longer get the "dfhack/" prefix if the string "dfhack/" already exists in the focus string
- ``Maps::GetBiomeTypeRef`` renamed to ``Maps::getBiomeTypeRef`` for consistency
- ``Maps::GetBiomeType`` renamed to ``Maps::getBiomeType`` for consistency
- ``Military``:
    - New module for military functionality
    - new ``makeSquad`` to create a squad
    - changed ``getSquadName`` to take a squad identifier
    - new ``updateRoomAssignments`` for assigning a squad to a barracks and archery range

Lua
---
- ``dfhack.job.attachJobItem()``: allows you to attach specific items to a job
- ``dfhack.screen.paintTile()``: you can now explicitly clear the interface cursor from a map tile by passing ``0`` as the tile value
- ``gui.INTERIOR_FRAME``: a panel frame style for use in highlighting off interior areas of a UI
- ``maps.getBiomeType``: exposed preexisting function to Lua
- ``widgets.CycleHotkeyLabel``: add ``label_below`` attribute for compact 2-line output
- ``widgets.FilteredList``: search key matching is now case insensitive by default
- ``widgets.Label``: token ``tile`` properties can now be functions that return a value

Structures
----------
- ``history_eventst``: Removed ``history_event_masterpiece_created_arch_designst`` and related enum value
- ``plot_infost``.``unk_8``: renamed to ``theft_intrigues``. Fields ``unk_1`` thru ``unk_8`` renamed to ``target_item``, ``mastermind_hf``, ``mastermind_plot_id``, ``corruptor_hf``, ``corruptor``, ``corruptee_hf``, ``corruptee``, and ``theft_agreement``. ``unk_1`` renamed to ``item_known_pos``.
- ``specific_ref_type``: Removed ``BUILDING_PARTY``, ``PETINFO_PET``, and ``PETINFO_OWNER`` enum values to fix alignment.


DFHack 50.07-alpha2
===================

New Scripts
-----------
- `combine`: combines stacks of food and plant items.

Fixes
-----
- `autobutcher`: implemented work-around for Dwarf Fortress not setting nicknames properly, so that nicknames created in the in-game interface are detected & protect animals from being butchered properly. Note that nicknames for unnamed units are not currently saved by dwarf fortress - use ``enable fix/protect-nicks`` to fix any nicknames created/removed within dwarf fortress so they can be saved/reloaded when you reload the game.
- `autochop`: generate default names for burrows with no assigned names
- `autodump`: changed behaviour to only change ``dump`` and ``forbid`` flags if an item is successfully dumped.
- `channel-safely`: fix an out of bounds error regarding the REPORT event listener receiving (presumably) stale id's
- `confirm`: fix fps drop when enabled
- `devel/query`: can now properly index vectors in the --table argument
- `forbid`: fix detection of unreachable items for items in containers
- `gui/blueprint`: correctly use setting presets passed on the commandline
- `gui/quickfort`: correctly use settings presets passed on the commandline
- `makeown`: fixes errors caused by using makeown on an invader
- `nestboxes`: fixed bug causing nestboxes themselves to be forbidden, which prevented citizens from using them to lay eggs. Now only eggs are forbidden.
- `seedwatch`: fix saving and loading of seed stock targets
- `tailor`: block making clothing sized for toads; make replacement clothing orders use the size of the wearer, not the size of the garment
- `troubleshoot-item`: fix printing of job details for chosen item
- `unforbid`: fix detection of unreachable items for items in containers
- ``Buildings::StockpileIterator``: fix check for stockpile items on block boundary.

Misc Improvements
-----------------
- DFHack tool windows that capture mouse clicks (and therefore prevent you from clicking on the "pause" button) now unconditionally pause the game when they open (but you can still unpause with the keyboard if you want to). Examples of this behavior: `gui/quickfort`, `gui/blueprint`, `gui/liquids`
- Stopped mouse clicks from affecting the map when a click on a DFHack screen dismisses the window
- `autobutcher`: logs activity to the console terminal instead of making disruptive in-game announcements
- `caravan`: add trade screen overlay that assists with selecting groups of items and collapsing groups in the UI
- `confirm`: configuration data is now persisted globally.
- `devel/query`: will now search for jobs at the map coordinate highlighted, if no explicit job is highlighted and there is a map tile highlighted
- `devel/visualize-structure`: now automatically inspects the contents of most pointer fields, rather than inspecting the pointers themselves
- `gui/gm-editor`: will now inspect a selected building itself if the building has no current jobs
- `showmood`: now shows the number of items needed for cloth and bars in addition to the technically correct but always confusing "total dimension" (150 per bar or 10,000 per cloth)
- `tailor`: add support for adamantine cloth (off by default); improve logging
- `troubleshoot-item`:
    - output as bullet point list with indenting, with item description and ID at top
    - reports on items that are hidden, artifacts, in containers, and held by a unit
    - reports on the contents of containers with counts for each contained item type

Removed
-------
- `combine-drinks`: replaced by `combine`
- `combine-plants`: replaced by `combine`

API
---
- Units module: added new predicates for ``isGeldable()``, ``isMarkedForGelding()``, and ``isPet()``
- ``Gui::any_civzone_hotkey``, ``Gui::getAnyCivZone``, ``Gui::getSelectedCivZone``: new functions to operate on the new zone system

Lua
---
- ``dfhack.gui.getSelectedCivZone``: returns the Zone that the user has selected currently
- ``widgets.FilteredList``: Added ``edit_on_change`` optional parameter to allow a custom callback on filter edit change.
- ``widgets.TabBar``: new library widget (migrated from control-panel.lua)

Structures
----------
- corrected alignment in ``world.status``
- identify item vmethod 213 (applies a thread improvements to appropriate items based on an RNG)
- identify two anons in ``difficultyst``
- identify various data types related to job completion/cancellation
- split ``gamest`` into ``gamest`` and ``gamest_extra`` to accommodate steam-specific data in ``gamest.mod_manager``
- ``activity_info``: ``unit_actor``, ``unit_noble``, and ``place`` converted from pointers to integer references.
- ``dipscript_popup``: ``meeting_holder`` converted from unit pointer into two unit refs ``meeting_holder_actor`` and ``meeting_holder_noble``.
- ``plotinfost``.``equipment``: Converted ``items_unmanifested``, ``items_unassigned``, and ``items_assigned`` vectors from pointers to item refs


DFHack 50.07-alpha1
===================

New Scripts
-----------
- `gui/design`: digging and construction designation tool with shapes and patterns
- `makeown`: makes the selected unit a citizen of your fortress

Fixes
-----
- Fix persisted data not being written on manual save
- Fix right click sometimes closing both a DFHack window and a vanilla panel
- Fixed issue with scrollable lists having some data off-screen if they were scrolled before being made visible
- `autochop`: fixed bug related to lua stack smashing behavior in returned stockpile configs
- `automelt`: fixed bug related to lua stack smashing behavior in returned stockpile configs
- `channel-safely`: fixed bug resulting in marker mode never being set for any designation
- `fix/protect-nicks`: now works by setting the historical figure nickname
- `gui/dig`: Fix for 'continuing' auto-stair designation. Avoid nil index issue for tile_type
- `gui/liquids`: fixed issues with unit pathing after adding/removing liquids
- `gui/unit-syndromes`: allow the window widgets to be interacted with
- `nestboxes`:
    - now cancels any in-progress hauling jobs when it protects a fertile egg
    - now scans for eggs more frequently and cancels any in-progress hauling jobs when it protects a fertile egg
- ``Units::isFortControlled``: Account for agitated wildlife

Misc Improvements
-----------------
- replaced DFHack logo used for the hover hotspot with a crisper image
- `autobutcher`:
    - changed defaults from 5 females / 1 male to 4 females / 2 males so a single unfortunate accident doesn't leave players without a mating pair
    - now immediately loads races available at game start into the watchlist
- `autodump`:
    - reinstate ``autodump-destroy-item``, hotkey: Ctrl-K
    - new hotkey for ``autodump-destroy-here``: Ctrl-H
- `automelt`: is now more resistent to vanilla savegame corruption
- `clean`: new hotkey for `spotclean`: Ctrl-C
- `dig`: new hotkeys for vein designation on z-level (Ctrl-V) and vein designation across z-levels (Ctrl-Shift-V)
- `gui/dig` : Added 'Line' shape that also can draw curves, added draggable center handle
- `gui/gm-editor`:
    - now supports multiple independent data inspection windows
    - now prints out contents of coordinate vars instead of just the type
- `hotkeys`: DFHack logo is now hidden on screens where it covers important information when in the default position (e.g. when choosing an embark site)
- `misery`: now persists state with the fort
- `orders`: recipe for silver crossbows removed from ``library/military`` as it is not a vanilla recipe, but is available in ``library/military_include_artifact_materials``
- `rejuvenate`: now takes an --age parameter to choose a desired age.
- `stonesense`: added an ``INVERT_MOUSE_Z`` option to invert the mouse wheel direction

Lua
---
- `overlay`: overlay widgets can now specify focus paths for the viewscreens they attach to so they only appear in specific contexts. see `overlay-dev-guide` for details.
- ``widgets.CycleHotkeyLabel``: Added ``key_back`` optional parameter to cycle backwards.
- ``widgets.FilteredList``: Added ``case_sensitive`` optional parameter to determine if filtering is case sensitive.
- ``widgets.HotkeyLabel``:
    - Added ``setLabel`` method to allow easily updating the label text without mangling the keyboard shortcut.
    - Added ``setOnActivate`` method to allow easily updating the ``on_activate`` callback.

Structures
----------
- added missing tiletypes and corrected a few old ones based on a list supplied by Toady


DFHack 50.05-alpha3.1
=====================

Fixes
-----
- `gui/launcher`: no longer resets to the Help tab on every keystroke
- `seedwatch`: fix parameter parsing when setting targets


DFHack 50.05-alpha3
===================

New Plugins
-----------
- `autoslab`: automatically create work orders to engrave slabs for ghostly dwarves

New Scripts
-----------
- `autofish`: auto-manage fishing labors to control your stock of fish
- `fix/civil-war`: removes negative relations with own government
- `fix/protect-nicks`: restore nicknames when DF loses them
- `forbid`: forbid and list forbidden items on the map
- `gui/autofish`: GUI config and status panel interface for autofish
- `gui/automelt`: GUI config and status panel interface for automelt
- `gui/control-panel`: quick access to DFHack configuration
- `gui/unit-syndromes`: browser for syndrome information

Fixes
-----
- allow launcher tools to launch themselves without hanging the game
- DF screens can no longer get "stuck" on transitions when DFHack tool windows are visible. Instead, those DF screens are force-paused while DFHack windows are visible so the player can close them first and not corrupt the screen sequence. The "PAUSE FORCED" indicator will appear on these DFHack windows to indicate what is happening.
- fix issues with clicks "passing through" some DFHack window elements to the screen below
- `autochop`: fixed a crash when processing trees with corrupt data structures (e.g. when a trunk tile fails to fall when the rest of the tree is chopped down)
- `autoclothing`: fixed a crash that can happen when units are holding invalid items.
- `build-now`: now correctly avoids adjusting non-empty tiles above constructions that it builds
- `catsplosion`: now only affects live, active units
- `getplants`: trees are now designated correctly
- `orders`:
    - fix orders in library/basic that create bags
    - library/military now sticks to vanilla rules and does not add orders for normally-mood-only platinum weapons. A new library orders file ``library/military_include_artifact_materials`` is now offered as an alternate ``library/military`` set of orders that still includes the platinum weapons.
- `quickfort`: allow floor bars, floor grates, and hatches to be placed over all stair types like vanilla allows

Misc Improvements
-----------------
- DFHack windows can now be "defocused" by clicking somewhere not over the tool window. This has the same effect as pinning previously did, but without the extra clicking.
- New borders for DFHack tool windows -- tell us what you think!
- Windows now display "PAUSE FORCED" on the lower border if the tool is forcing the game to pause
- `autoclothing`: merged the two separate reports into the same command.
- `automelt`: stockpile configuration can now be set from the commandline
- `ban-cooking`:
    - ban announcements are now hidden by default; use new option ``--verbose`` to show them.
    - report number of items banned.
- `build-now`: now handles dirt roads and initializes farm plots properly
- `channel-safely`: new monitoring for cave-in prevention
- `devel/click-monitor`: report on middle mouse button actions
- `getplants`: ID values will now be accepted regardless of case
- `gui/autochop`: hide uninteresting burrows by default
- `gui/blueprint`: allow map movement with the keyboard while the UI is open
- `gui/control-panel`:
    - you can now configure whether DFHack tool windows should pause the game by default
    - new global hotkey for quick access: Ctrl-Shift-E
- `gui/create-item`:
    - support spawning corpse pieces (e.g. shells) under "body part"
    - added search and filter capabilities to the selection lists
    - added whole corpse spawning alongside corpsepieces. (under "corpse")
- `gui/launcher`:
    - sped up initialization time for faster window appearance
    - make command output scrollback separate from the help text so players can continue to see the output of the previous command as they type the next one
    - allow double spacebar to pause/unpause the game, even while typing a command
    - clarify what is being shown in the autocomplete list (all commands, autocompletion of partially typed command, or commands related to typed command)
    - support running commands directly from the autocomplete list via double-clicking
- `gui/liquids`: interface overhaul, also now allows spawning river sources, setting/adding/removing liquid levels, and cleaning water from being salty or stagnant
- `gui/overlay`: now focuses on repositioning overlay widgets; enabling, disabling, and getting help for overlay widgets has moved to the new `gui/control-panel`
- `gui/quickcmd`:
    - now has its own global keybinding for your convenience: Ctrl-Shift-A
    - now acts like a regular window instead of a modal dialog
- `gui/quickfort`: don't close the window when applying a blueprint so players can apply the same blueprint multiple times more easily
- `hotkeys`: clicking on the DFHack logo no longer closes the popup menu
- `locate-ore`: now only searches revealed tiles by default
- `modtools/spawn-liquid`: sets tile temperature to stable levels when spawning water or magma
- `nestboxes`: now saves enabled state in your savegame
- `orders`: orders plugin functionality is now accessible via an `overlay` widget when the manager orders screen is open
- `prioritize`:
    - pushing minecarts is now included in the default prioritization list
    - now automatically starts boosting the default list of job types when enabled
- `quickfort`: planned buildings are now properly attached to any pertinent overlapping zones
- `seedwatch`: now persists enabled state in the savegame, automatically loads useful defaults, and respects reachability when counting available seeds
- `unforbid`: avoids unforbidding unreachable and underwater items by default

Documentation
-------------
- Quickstart guide has been updated with info on new window behavior and how to use the control panel
- `compile`: instructions added for cross-compiling DFHack for Windows from a Linux Docker builder

Removed
-------
- `autohauler`: no plans to port to v50, as it just doesn't make sense with the new work detail system
- `show-unit-syndromes`: replaced by `gui/unit-syndromes`; html export is no longer supported

API
---
- `overlay`: overlay widgets can now specify a default enabled state if they are not already set in the player's overlay config file
- ``Buildings::containsTile()``: no longer takes a ``room`` parameter since that's not how rooms work anymore. If the building has extents, the extents will be checked. otherwise, the result just depends on whether the tile is within the building's bounding box.
- ``Lua::Push``: now supports ``std::unordered_map``
- ``Screen::Pen``: now accepts ``top_of_text`` and ``bottom_of_text`` properties to support offset text in graphics mode
- ``Units::getCitizens()``: gets a list of citizens, which otherwise you'd have to iterate over all units the world to discover

Lua
---
- `helpdb`:
    - new function: ``helpdb.refresh()`` to force a refresh of the database. Call if you are a developer adding new scripts, loading new plugins, or changing help text during play
    - changed from auto-refreshing every 60 seconds to only refreshing on explicit call to ``helpdb.refresh()``. docs very rarely change during a play session, and the automatic database refreshes were slowing down the startup of `gui/launcher` and anything else that displays help text.
- `tiletypes`: now has a Lua API! ``tiletypes_setTile``
- ``dfhack.units.getCitizens()``: gets a list of citizens
- ``gui.ZScreen``: new attribute: ``defocusable`` for controlling whether a window loses keyboard focus when the map is clicked
- ``widgets.Label``:
    - ``label.scroll()`` now understands ``home`` and ``end`` keywords for scrolling to the top or bottom
    - token ``tile`` properties can now be either pens or numeric texture ids
- ``widgets.List``: new callbacks for double click and shift double click

Structures
----------
- add "hospital" language name category
- corrected misalignment in ``unitst`` (affecting ``occupation`` and ``adjective``)
- identified fields for squads and other military structures
- identified some anons in ``unitst`` related to textures (thanks, putnam)
- identify a table of daily events scheduled to take place in the current year
- realigned and fleshed out ``entity_site_link`` (again, thanks, putnam)
- remove some no-longer-valid reputation types
- ``building_design``: corrected misalignments
- ``creature_raw_graphics``: corrected misalignments
- ``item.setSharpness()``: more info about params
- ``occupation_type``: add enum values for new occupations related to hospitals


DFHack 50.05-alpha2
===================

Fixes
-----
- `autofarm`: don't duplicate status line entries for crops with no current supply
- `build-now`: don't error on constructions that do not have an item attached
- `gui/gm-editor`: fix errors displayed while viewing help screen
- `orders`: allow the orders library to be listed and imported properly (if you previously copied the orders library into your ``dfhack-config/orders`` directory to work around this bug, you can remove those files now)
- `tailor`: now respects the setting of the "used dyed clothing" standing order toggle

Removed
-------
- `create-items`: replaced by `gui/create-item` ``--multi``

Structures
----------
- corrected misalignment in ``historical_entity``
- identified two old and one new language name groups
- partially identified squad-related structures in ``plotinfo`` and corrected position of ``civ_alert_idx`` (does not affect alignment)


DFHack 50.05-alpha1
===================

New Scripts
-----------
- `allneeds`: list all unmet needs sorted by how many dwarves suffer from them.
- `devel/tile-browser`: page through available textures and see their texture ids
- `gui/autochop`: configuration frontend and status monitor for the `autochop` plugin

Fixes
-----
- `make-legendary`: "MilitaryUnarmed" option now functional
- ``widgets.WrappedLabel``: no longer resets scroll position when window is moved or resized

Misc Improvements
-----------------
- Scrollable widgets now react to mouse wheel events when the mouse is over the widget
- the ``dfhack-config/scripts/`` folder is now searched for scripts by default
- `autounsuspend`: now saves its state with your fort
- `devel/inspect-screen`: updated for new rendering semantics and can now also inspect map textures
- `emigration`: now saves its state with your fort
- `exterminate`: added drown method. magma and drown methods will now clean up liquids automatically.
- `gui/cp437-table`: converted to a movable, mouse-enabled window
- `gui/gm-editor`: converted to a movable, resizable, mouse-enabled window
- `gui/gm-unit`: converted to a movable, resizable, mouse-enabled window
- `gui/launcher`:
    - now supports a smaller, minimal mode. click the toggle in the launcher UI or start in minimal mode via the ``Ctrl-Shift-P`` keybinding
    - can now be dragged from anywhere on the window body
    - now remembers its size and position between invocations
- `gui/quickcmd`:
    - converted to a movable, resizable, mouse-enabled window
    - commands are now stored globally so you don't have to recreate commands for every fort
- `hotkeys`: overlay hotspot widget now shows the DFHack logo in graphics mode and "DFHack" in text mode
- `prioritize`: now saves its state with your fort
- `script-paths`: removed "raw" directories from default script paths. now the default locations to search for scripts are ``dfhack-config/scripts``, ``save/*/scripts``, and ``hack/scripts``
- `unsuspend`:
    - overlay now displays different letters for different suspend states so they can be differentiated in graphics mode (P=planning, x=suspended, X=repeatedly suspended)
    - overlay now shows a marker all the time when in graphics mode.  ascii mode still only shows when paused so that you can see what's underneath.
- ``init.d``: directories have moved from the ``raw`` subfolder (which no longer exists) to the root of the main DF folder or a savegame folder

Documentation
-------------
- added DFHack architecture diagrams to the dev intro
- added DFHack Quickstart guide
- `devel/hello-world`: updated to be a better example from which to start new gui scripts
- `overlay-dev-guide`: added troubleshooting tips and common development workflows

Removed
-------
- Ruby is no longer a supported DFHack scripting language
- ``fix-job-postings`` from the `workflow` plugin is now obsolete since affected savegames can no longer be loaded

API
---
- ``Gui::getDFViewscreen``: returns the topmost underlying DF viewscreen
- ``Gui::getDwarfmodeDims``: now only returns map viewport dimensions; menu dimensions are obsolete
- ``Screen::Pen``: now accepts ``keep_lower`` and ``write_to_lower`` properties to support foreground and background textures in graphics mode

Lua
---
- Removed ``os.execute()`` and ``io.popen()`` built-in functions
- `overlay`: ``OverlayWidget`` now inherits from ``Panel`` instead of ``Widget`` to get all the frame and mouse integration goodies
- ``dfhack.gui.getDFViewscreen()``: returns the topmost underlying DF viewscreen
- ``gui.CLEAR_PEN``: now clears the background and foreground and writes to the background (before it would always write to the foreground)
- ``gui.KEEP_LOWER_PEN``: a general use pen that writes associated tiles to the foreground while keeping the existing background
- ``gui.View``:
    - ``visible`` and ``active`` can now be functions that return a boolean
    - new function ``view:getMouseFramePos()`` for detecting whether the mouse is within (or over) the exterior frame of a view
- ``gui.ZScreen``: Screen subclass that implements window raising, multi-viewscreen input handling, and viewscreen event pass-through so the underlying map can be interacted with and dragged around while DFHack screens are visible
- ``widgets.CycleHotkeyLabel``:
    - now supports rendering option labels in the color of your choice
    - new functions ``setOption()`` and ``getOptionPen()``
- ``widgets.Label``: tiles can now have an associated width
- ``widgets.Panel``: new attributes to control window dragging and resizing with mouse or keyboard
- ``widgets.ToggleHotkeyLabel``: now renders the ``On`` option in green text
- ``widgets.Window``: Panel subclass with attributes preset for top-level windows

Structures
----------
- Renamed globals to match DF:
    - ``ui``: renamed to ``plotinfo``
    - ``ui_advmode``: renamed to ``adventure``
    - ``ui_build_selector``: renamed to ``buildreq``
    - ``ui_sidebar_menus``: renamed to ``game``
- ``building_civzonest``: identify two variables, ``dir_x`` and ``dir_y``, that handle archery range direction.


