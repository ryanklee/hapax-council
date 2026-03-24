--[[
    This file sets up the global state for the procedural generation scripts.
    It's probably best that you don't mess with it. Mods can add onto the global
    state on their own anyway, so this file shouldn't need to be modified ever.
]]

languages = {}

preprocess = {
    demon=function()
        local rop=random_object_parameters
        local left=rop.demon_def_number
        rop.demons_to_gen={} -- you can just add to the random object parameters, it's okay, use it to hold stuff
        if left > 0 then
            local amt=math.floor((left+4)/5)
            local small_amt=math.floor(amt/2)
            local large_amt = amt-small_amt
            for i=1,large_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="flying_spirit",difficulty=10}
            end
            for i=1,small_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="flying_spirit",difficulty=6}
            end
            left = left - amt
        end
        if left > 0 then
            local amt=math.floor((left+3)/4)
            for i=1,amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="unique",difficulty=10}
            end
            left = left - amt
        end
        if left > 0 then
            local amt=math.floor((left+2)/3)
            local small_amt=math.floor(amt/2)
            local large_amt = amt-small_amt
            for i=1,large_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="humanoid_beast",difficulty=10}
            end
            for i=1,small_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="humanoid_beast",difficulty=6}
            end
            left = left - amt
        end
        if left > 0 then 
            local amt=math.floor((left+1)/2)
            local small_amt=math.floor(amt/2)
            local large_amt = amt-small_amt
            for i=1,large_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="beast",difficulty=10}
            end
            for i=1,small_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="beast",difficulty=6}
            end
            left = left - amt
        end
        if left > 0 then
            local amt = left
            local small_amt=math.floor(amt/2)
            local large_amt=left-small_amt
            for i=1,large_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="whatever",difficulty=10}
            end
            for i=1,small_amt do
                rop.demons_to_gen[#rop.demons_to_gen+1]={demon_type="whatever",difficulty=6}
            end
        end
    end,
    bogeyman_polymorph=function()
        if random_object_parameters.night_creature_def_number_bogeyman>0 then
            local lines={}
            lines[#lines+1]="[INTERACTION:"..random_object_parameters.token_prefix.."BOGEYMAN_POLYMORPH]"
            add_generated_info(lines)
            lines[#lines+1]="[I_SOURCE:CREATURE_ACTION]"
            lines[#lines+1]="[I_TARGET:A:CREATURE]"
            lines[#lines+1]="    [IT_LOCATION:CONTEXT_CREATURE]"
            lines[#lines+1]="[I_EFFECT:ADD_SYNDROME]"
            lines[#lines+1]="    [IE_TARGET:A]"
            lines[#lines+1]="    [IE_IMMEDIATE]"
            lines[#lines+1]="    [SYNDROME]"
            lines[#lines+1]="        [SYN_CONCENTRATION_ADDED:1000:0] just in case"
            lines[#lines+1]="        [CE_BODY_TRANSFORMATION:START:0:PEAK:0:END:5:ABRUPT:DWF_STRETCH:144]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_FLAG:SMALL_RACE]"
            lines[#lines+1]="            [CE:CREATURE_CASTE_FLAG:LARGE_PREDATOR]"
            lines[#lines+1]="            [CE:CREATURE_CASTE_FLAG:NATURAL_ANIMAL]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:CANNOT_BREATHE_AIR]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:IMMOBILE_LAND]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:CAN_LEARN]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:MEGABEAST]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:SEMIMEGABEAST]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:TITAN]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:DEMON]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:UNIQUE_DEMON]"
            lines[#lines+1]="            [CE:FORBIDDEN_CREATURE_CASTE_FLAG:SUPERNATURAL]"
            lines[#lines+1]="        [CE_ADD_TAG:NO_AGING:START:0:PEAK:0:END:5:ABRUPT:DWF_STRETCH:144]"
            raws.register_interactions(lines)
        end
    end
}

do_once_early={}

do_once={
    rcp_mat_emission=function()
        local lines={}
        lines[#lines+1]="[INTERACTION:RCP_MATERIAL_EMISSION]"
        add_generated_info(lines)
        lines[#lines+1]="[I_SOURCE:CREATURE_ACTION]"
        lines[#lines+1]="[I_TARGET:A:MATERIAL]"
        lines[#lines+1]="    [IT_MATERIAL:CONTEXT_MATERIAL]"
        lines[#lines+1]="[I_TARGET:B:LOCATION]"
        lines[#lines+1]="    [IT_LOCATION:CONTEXT_LOCATION]"
        lines[#lines+1]="[I_TARGET:C:LOCATION]"
        lines[#lines+1]="    [IT_LOCATION:CONTEXT_LOCATION]"
        lines[#lines+1]="    [IT_MANUAL_INPUT:target]"
        lines[#lines+1]="[I_EFFECT:MATERIAL_EMISSION]"
        lines[#lines+1]="    [IE_TARGET:A]"
        lines[#lines+1]="    [IE_TARGET:B]"
        lines[#lines+1]="    [IE_TARGET:C]"
        lines[#lines+1]="    [IE_IMMEDIATE]"
        raws.register_interactions(lines)
    end,
}

postprocess={}

unittests={
    get_creature=function()
        local cr=world.creature.creature[1]
        local res={}
        res.good=type(cr)=='table'
        res.info=res.good and ("1st creature is "..cr.token) or "No creature at index 1! Function not working correctly?"
        return res
    end,
    get_random_creature=function()
        local cr=world.creature.get_random_creature()
        local res={}
        res.good=type(cr)=='table'
        res.info=res.good and ("Got a random creature: "..cr.token) or "No random creature could be gotten, even at most permissive!"
        return res
    end,
    get_random_creature_with_flag=function()
        local cr=world.creature.get_random_creature("HAS_ANY_INTELLIGENT_LEARNS")
        local res={}
        res.good=type(cr)=='table' and cr.flags.HAS_ANY_INTELLIGENT_LEARNS
        if type(cr)=='table' and not cr.flags.HAS_ANY_INTELLIGENT_LEARNS then
            res.info="Got a random creature: "..cr.token..", but it's not intelligent!"
        elseif res.good then
            res.info="Got a random intelligent creature: "..cr.token
        else
            res.info="No random intelligent creature gotten!"
        end
        return res
    end,
    push_every_kind_of_thing=function()
        local res={}
        res.good,res.info=pcall(function() log_table(world,2,0,0.5) end )
        if res.good then
            res.info="No errors in printing world."
        end
        return res
    end
}

materials = {
    divine = {
        metal = {},
        silk = {}
    },
    clouds={},
    rain={},
    mythical_remnant={},
    mythical_healing={},
}

items={
    instruments={
        keyboard={},
        stringed={},
        wind={},
        percussion={}
    },
}

creatures={
    fb={},
    titan={},
    demon={},
    night_creature={
        troll={},
        -- most of these are unused, as of yet
        vampire={},
        werebeast={},
        ghost={},
        walking_dead_thinking={},
        walking_dead_dumb_animated={},
        water={},
        stalker={},
        animated={},
        bogeyman={},
        ocean={},
        natural={},
        constructed={},
        sorcerer={},
        royal={},
        nightmare={},
    },
    experiment={
        humanoid={},
        humanoid_giant={},
        beast_small={},
        beast_large={},
        failed_small={},
        failed_large={},
    },
    angel={
        humanoid_warrior={},
        humanoid_generic={},
        great_beast={}
    },
}

interactions={
    underground_special={},
    regional={},
    secrets={},
    disturbance={},
    blessing={
        minor={},
        medium={},
        major={}
    },
    curse={
        minor={},
        medium={},
        major={}
    },
    bogeyman={},
    mythical_item_power={},
    mythical={},
}

entities={
    vault_guardian={},
    mythical_guardian={}
}

function add_generated_info(tbl)
    tbl[#tbl+1]="[GENERATED]"
    if random_object_parameters.source_hfid~=-1 then
        tbl[#tbl+1]="[SOURCE_HFID:"..random_object_parameters.source_hfid.."]"
    end
    if random_object_parameters.source_enid~=-1 then
        tbl[#tbl+1]="[SOURCE_ENID:"..random_object_parameters.source_enid.."]"
    end
    return tbl
end

function generate()
    local l=get_debug_logger(0.5)
    if debug_level>0 then
        for name,test in pairs(unittests) do
            local res=test()
            log("Test "..name.." "..(res.good and "SUCCEEDED" or "FAILED")..(res.info and (": "..res.info) or ""))
        end
    end
    l("Starting generation...")
    for k,v in pairs(preprocess) do -- Every time generate() is run (you cannot predict when this happens!)
        v()
    end
    if random_object_parameters.pre_gen_randoms then
        for k,v in pairs(do_once_early) do -- At the start of worldgen, before map generation
            v()
        end
    end
    if random_object_parameters.main_world_randoms then
        for k,v in pairs(do_once) do -- A step in "generating prehistory", right before history starts
            v()
        end
    end
    -- Vanilla processing
    l("Starting materials...")
    generate_random_materials()
    l("Starting items...")
    generate_random_items()
    if random_object_parameters.main_world_randoms then
        l("Starting languages...")
        generate_random_languages()
    end
    l("Starting creatures...")
    generate_random_creatures()
    l("Starting interactions...")
    generate_random_interactions()
    l("Starting entities...")
    generate_random_entities()
    l("Finishing...")
    for k,v in pairs(postprocess) do
        v()
    end
    l("Done...")
end

function generate_random_materials()
    local lines={}
    local l=get_debug_logger(2)
    if random_object_parameters.use_divine_materials then
        local cind=1
        local pos_sphere={metal={},silk={}}
        local have={metal={},silk={}}
        for k,v in pairsByKeys(world.spheres) do
            pos_sphere.metal[#pos_sphere.metal+1]=k
            pos_sphere.silk[#pos_sphere.silk+1]=k
        end
        local we_have_made_enough_divine_mats=false
        local force_stop=false
        repeat
            for i=1,20 do
                local good=false
                local m_type=(i%2 == 1) and "metal" or "silk"
                repeat
                    local sph=pick_random_no_replace(pos_sphere[m_type])
                    if not sph then
                        force_stop=true
                        l("Ran out of spheres to generate with!")
                    end
                    local m=generate_from_list(materials.divine[m_type],sph)
                    local generated_tbl = m and (m.mat or m.raws)
                    if generated_tbl then
                        l(sph," It's good!")
                        good=true
                        lines[#lines+1]="[INORGANIC:"..random_object_parameters.token_prefix.."DIVINE_"..tostring(cind).."]"
                        cind = cind+1
                        add_generated_info(lines)
                        lines[#lines+1]="[DIVINE]"
                        table_merge(lines,generated_tbl)
                        lines[#lines+1]="[SPHERE:"..sph.."]"
                        have[m_type][sph]=true
                    end
                until good or force_stop
                if force_stop then break end
            end
            we_have_made_enough_divine_mats=true
            --IS ALL OF THE COSMOS REPRESENTED OR AT LEAST NEUTRAL TO THE SITUATION?
            for k,v in pairsByKeys(world.spheres) do
                local met,slk=false,false
                for kk,vv in pairs(have.metal) do
                    met=met or not v.enemies[kk]
                end
                for kk,vv in pairs(have.silk) do
                    slk=slk or not v.enemies[kk]
                end
                if not met or not slk then
                    we_have_made_enough_divine_mats=false
                end
            end
        until we_have_made_enough_divine_mats or force_stop
    end
    for i=1,random_object_parameters.evil_cloud_number do
        random_object_parameters.cloud_states=random_object_parameters.cloud_states or {}
        local res=generate_from_list(materials.clouds)
        local generated_tbl = res and (res.mat or res.raws)
        if generated_tbl then
            lines[#lines+1]="[INORGANIC:"..random_object_parameters.token_prefix.."EVIL_CLOUD_"..tostring(i).."]"
            add_generated_info(lines)
            lines[#lines+1]="[SPECIAL]"
            table_merge(lines,generated_tbl)
            random_object_parameters.cloud_states[i]=res.state
        end
    end
    for i=1,random_object_parameters.evil_rain_number do
        local res=generate_from_list(materials.rain)
        local generated_tbl = res and (res.mat or res.raws)
        if generated_tbl then
            lines[#lines+1]="[INORGANIC:"..random_object_parameters.token_prefix.."EVIL_RAIN_"..tostring(i).."]"
            add_generated_info(lines)
            lines[#lines+1]="[SPECIAL]"
            table_merge(lines,generated_tbl)
        end
    end
    if random_object_parameters.use_mythical_materials then
        local cind=1
        for sph,_ in pairsByKeys(random_object_parameters.mythical_sphere) do
            local res=generate_from_list(materials.mythical_remnant,sph)
            local generated_tbl = res and (res.mat or res.raws)
            if generated_tbl then
                lines[#lines+1]="[INORGANIC:"..random_object_parameters.token_prefix.."MYTHICAL_REMNANT_"..tostring(cind).."]"
                cind = cind+1
                add_generated_info(lines)
                lines[#lines+1]="[MYTHICAL_REMNANT]"
                table_merge(lines,generated_tbl)
            end
        end
    end
    if random_object_parameters.allow_mythical_healing then
        for i=1,5 do
            local res=generate_from_list(materials.mythical_healing)
            local generated_tbl = res and (res.mat or res.raws)
            if generated_tbl then
                lines[#lines+1]="[INORGANIC:"..random_object_parameters.token_prefix.."MYTHICAL_SUBSTANCE_"..tostring(i).."]"
                add_generated_info(lines)
                lines[#lines+1]="[SPECIAL]"
                lines[#lines+1]="[MYTHICAL_SUBSTANCE]"
                table_merge(lines,generated_tbl)
            end
        end
    end
    raws.register_inorganics(lines)
end

function generate_random_items()
    --todo
    --[[
    local lines={}
    raws.register_items(lines)
    ]]
end

function generate_random_languages()
    local lines={}
    for k,v in pairsByKeys(languages) do
        lines[#lines+1]="[TRANSLATION:"..k.."]"
        add_generated_info(lines)
        local language_by_word=v()
        for kk,vv in ipairs(world.language.word) do
            local tok=vv.token
            lines[#lines+1]="[T_WORD:"..tok..":"..language_by_word[tok].."]"
        end
    end
    raws.register_languages(lines)
end

function generate_random_creatures()
    local ropar = random_object_parameters
    ropar.demons_to_gen = ropar.demons_to_gen or {}
    local l = get_debug_logger()
    local l2 = get_debug_logger(2)
    local tbl={}
    l("Starting creatures...")
    for k,v in ipairs(ropar.layer_type) do
        local tok=ropar.token_prefix.."FORGOTTEN_BEAST_"..tostring(k)
        local c=generate_from_list(creatures.fb,v,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            l(tok)
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.titan_def_number do
        local tok=ropar.token_prefix.."TITAN_"..tostring(i)
        local c=generate_from_list(creatures.titan,ropar.titan_subreg[i],tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            l(tok)
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for k,v in ipairs(ropar.demons_to_gen) do
        local tok=ropar.token_prefix.."DEMON_"..tostring(k)
        local c=generate_from_list(creatures.demon,v.demon_type,v.difficulty,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            l(tok)
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    local night_creature_count=1
    for i=1,ropar.night_creature_def_number_troll do
        local tok=ropar.token_prefix.."NIGHT_CREATURE_"..tostring(night_creature_count)
        local c=generate_from_list(creatures.night_creature.troll,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            night_creature_count=night_creature_count+1
        end
    end
    for i=1,ropar.night_creature_def_number_bogeyman do
        local tok=ropar.token_prefix.."NIGHT_CREATURE_"..tostring(night_creature_count)
        local c=generate_from_list(creatures.night_creature.bogeyman,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            night_creature_count=night_creature_count+1
        end
    end
    for i=1,ropar.night_creature_def_number_nightmare do
        local tok=ropar.token_prefix.."NIGHT_CREATURE_"..tostring(night_creature_count)
        local c=generate_from_list(creatures.night_creature.nightmare,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            night_creature_count=night_creature_count+1
        end
    end
    for i=1,ropar.interaction_def_number_deity_curse_werebeast do
        local tok=ropar.token_prefix.."NIGHT_CREATURE_"..tostring(night_creature_count)
        local c=generate_from_list(creatures.night_creature.werebeast,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            night_creature_count=night_creature_count+1
        end
    end
    local angel_count=1
    for i=1,ropar.angel_def_number_humanoid_warrior do
        local tok=ropar.token_prefix.."DIVINE_"..tostring(angel_count)
        local c=generate_from_list(creatures.angel.humanoid_warrior,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            angel_count=angel_count+1
        end
    end
    for i=1,ropar.angel_def_number_humanoid_generic do
        local tok=ropar.token_prefix.."DIVINE_"..tostring(angel_count)
        local c=generate_from_list(creatures.angel.humanoid_generic,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            angel_count=angel_count+1
        end
    end
    for i=1,ropar.angel_def_number_great_beast do
        local tok=ropar.token_prefix.."DIVINE_"..tostring(angel_count)
        local c=generate_from_list(creatures.angel.great_beast,tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
            angel_count=angel_count+1
        end
    end
    if ropar.making_experiment then
        local exp_token={
            humanoid="E_HUM",
            humanoid_giant="E_HUMG",
            beast_small="E_BEAST",
            beast_large="E_BEASTL",
            failed_small="E_FS",
            failed_large="E_FL",
        }
        local tok=ropar.token_prefix..exp_token[ropar.making_experiment]..tostring(ropar.experimenter_experiment_count+1)
        local c=generate_from_list(creatures.experiment[ropar.making_experiment],tok)
        local generated_tbl = c and (c.creature or c.raws)
        if generated_tbl then
            tbl[#tbl+1]="[CREATURE:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl=table_merge(tbl,generated_tbl)
            l(tok)
        end
    end
    l("done")
    if debug_level>=1 then
        print_table(tbl)
    end
    raws.register_creatures(tbl)
end

function generate_random_interactions()
    local ropar = random_object_parameters
    local tbl={}
    local l=get_debug_logger()
    local l2=get_debug_logger(2)
    local evil_mats={}
    l("Starting interactions...")
    for i=1,ropar.evil_cloud_number do
        evil_mats[#evil_mats+1]=function(lines)
            lines[#lines+1]="[I_TARGET:B:MATERIAL]"
            local material_s="[IT_MATERIAL:MATERIAL:INORGANIC:"..ropar.token_prefix.."EVIL_CLOUD_"..tostring(i)
            if ropar.cloud_states[i]=="GAS" then
                material_s=material_s..":WEATHER_CREEPING_GAS]"
            elseif ropar.cloud_states[i]=="LIQUID" then
                material_s=material_s..":WEATHER_CREEPING_VAPOR]"
            else
                material_s=material_s..":WEATHER_CREEPING_DUST]"
            end
            lines[#lines+1]=material_s
            lines[#lines+1]="[I_EFFECT:MATERIAL_EMISSION]"
            lines[#lines+1]="   [IE_TARGET:B]"
            lines[#lines+1]="   [IE_INTERMITTENT:WEEKLY]"
        end
    end
    for i=1,ropar.evil_rain_number do
        evil_mats[#evil_mats+1]=function(lines)
            lines[#lines+1]="[I_TARGET:B:MATERIAL]"
            lines[#lines+1]="[IT_MATERIAL:MATERIAL:INORGANIC:"..ropar.token_prefix.."EVIL_RAIN_"..tostring(i)..":WEATHER_FALLING_MATERIAL]"
            lines[#lines+1]="[I_EFFECT:MATERIAL_EMISSION]"
            lines[#lines+1]="   [IE_TARGET:B]"
            lines[#lines+1]="   [IE_INTERMITTENT:WEEKLY]"
        end
    end
    for k,v in ipairs(world.usable_blood_materials) do
        evil_mats[#evil_mats+1]=function(lines)
            lines[#lines+1]="[I_TARGET:B:MATERIAL]"
            lines[#lines+1]="[IT_MATERIAL:MATERIAL:CREATURE_MAT:"..v..":WEATHER_FALLING_MATERIAL]"
            lines[#lines+1]="[I_EFFECT:MATERIAL_EMISSION]"
            lines[#lines+1]="   [IE_TARGET:B]"
            lines[#lines+1]="   [IE_INTERMITTENT:WEEKLY]"
        end
    end
    for i=1,ropar.interaction_def_number_regional do
        local region_tbl={}
        region_tbl[#region_tbl+1]="[INTERACTION:"..ropar.token_prefix.."REGIONAL_"..tostring(i).."]"
        region_tbl=add_generated_info(region_tbl)
        region_tbl[#region_tbl+1]="[I_SOURCE:REGION]"
        region_tbl[#region_tbl+1]="  [IS_REGION:EVIL_ONLY]"
        region_tbl[#region_tbl+1]="  [IS_REGION:SAVAGE_ALLOWED]"
        region_tbl[#region_tbl+1]="  [IS_REGION:ANY_TERRAIN]"
        region_tbl[#region_tbl+1]="  [IS_FREQUENCY:100]" -- How do we make this in particular smarter?
        local did_animation=false
        local any_good=false
        if #evil_mats==0 or one_in(2) then
            local t=generate_from_list(interactions.regional)
            local generated_tbl = t and (t.interaction or t.raws)
            if generated_tbl then
                region_tbl=table_merge(region_tbl,generated_tbl)
                did_animation=true
                any_good=true
            end
        end
        if #evil_mats>0 and (one_in(2) or not did_animation) then
            pick_random(evil_mats)(region_tbl)
            any_good=true
        end
        if any_good then
            tbl=table_merge(tbl,region_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_secret do
        local t=generate_from_list(interactions.secrets,i)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            tbl[#tbl+1]="[INTERACTION:"..ropar.token_prefix.."SECRET_"..tostring(i.."]")
            tbl=add_generated_info(tbl)
            tbl[#tbl+1]="[I_SOURCE:SECRET]"
            --spent a while agonizing over adding something to try to more evenly distribute spheres; it's a maybe?
            l2(ropar.token_prefix.."SECRET_"..tostring(i))
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_disturbance do
        local t=generate_from_list(interactions.disturbance,i)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            local token=ropar.token_prefix.."DISTURBANCE_"..tostring(i)
            tbl[#tbl+1]="[INTERACTION:"..token.."]"
            tbl=add_generated_info(tbl)
            tbl[#tbl+1]="[I_SOURCE:DISTURBANCE]"
            l2(ropar.token_prefix.."DISTURBANCE_"..tostring(i))
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_minor_blessing do
        local t=generate_from_list(interactions.blessing.minor,i)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            local token=ropar.token_prefix.."MINOR_BLESSING_"..tostring(i)
            tbl[#tbl+1]="[INTERACTION:"..token.."]"
            l2(ropar.token_prefix.."MINOR_BLESSING_"..tostring(i))
            tbl=add_generated_info(tbl)
            tbl=split_to_lines(tbl,[[
                [I_SOURCE:DEITY]
                    [IS_USAGE_HINT:MINOR_BLESSING]
            ]])
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_medium_blessing do
        local t=generate_from_list(interactions.blessing.medium,i)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            local token=ropar.token_prefix.."MEDIUM_BLESSING_"..tostring(i)
            tbl[#tbl+1]="[INTERACTION:"..token.."]"
            l2(ropar.token_prefix.."MEDIUM_BLESSING_"..tostring(i))
            tbl=add_generated_info(tbl)
            tbl=split_to_lines(tbl,[[
                [I_SOURCE:DEITY]
                    [IS_USAGE_HINT:MEDIUM_BLESSING]
            ]])
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_minor_curse do
        local t=generate_from_list(interactions.curse.minor,i)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            local token=ropar.token_prefix.."MINOR_CURSE_"..tostring(i)
            tbl[#tbl+1]="[INTERACTION:"..token.."]"
            l2(ropar.token_prefix.."MINOR_CURSE_"..tostring(i))
            tbl=add_generated_info(tbl)
            tbl=split_to_lines(tbl,[[
                [I_SOURCE:DEITY]
                    [IS_USAGE_HINT:MINOR_CURSE]
            ]])
            tbl=table_merge(tbl,generated_tbl)
        end
    end    
    for i=1,ropar.interaction_def_number_medium_curse do
        local t=generate_from_list(interactions.curse.medium,i)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            local token=ropar.token_prefix.."MEDIUM_CURSE_"..tostring(i)
            tbl[#tbl+1]="[INTERACTION:"..token.."]"
            l2(ropar.token_prefix.."MEDIUM_CURSE_"..tostring(i))
            tbl=add_generated_info(tbl)
            tbl=split_to_lines(tbl,[[
                [I_SOURCE:DEITY]
                    [IS_USAGE_HINT:MEDIUM_CURSE]
            ]])
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_deity_curse_vampire do -- rename?
        local token=ropar.token_prefix.."DEITY_MAJOR_CURSE_"..tostring(i)
        local t=generate_from_list(interactions.curse.major,i,token)
        local generated_tbl = t and (t.interaction or t.raws)
        if generated_tbl then
            tbl[#tbl+1]="[INTERACTION:"..token.."]"
            l2(token)
            tbl=add_generated_info(tbl)
            tbl[#tbl+1]="[I_SOURCE:DEITY]"
            tbl[#tbl+1]="    [IS_USAGE_HINT:MAJOR_CURSE]"
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,ropar.interaction_def_number_mythical do
        for lv=0,3 do
            local token=ropar.token_prefix.."MYTHICAL_"..tostring(i).."_"..tostring(lv)
            local sph=pick_random(ropar.mythical_sphere) or "CHAOS"
            local t=generate_from_list(interactions.mythical,i,lv,sph)
            local generated_tbl = t and (t.interaction or t.raws)
            if generated_tbl then
                tbl[#tbl+1]="[INTERACTION:"..token.."]"
                l2(token)
                tbl=add_generated_info(tbl)
                tbl[#tbl+1]="[I_SOURCE:MYTHICAL]"
                tbl[#tbl+1]="[IS_POWER_LEVEL:"..tostring(lv).."]"
                tbl[#tbl+1]="[I_TARGET:A:CREATURE]"
                tbl[#tbl+1]="[IT_LOCATION:CONTEXT_CREATURE]"
                tbl[#tbl+1]="[IT_REQUIRES:CAN_LEARN]"
                tbl[#tbl+1]="[IT_REQUIRES:CAN_SPEAK]"
                tbl=table_merge(tbl,generated_tbl)
            end
        end
    end
    if ropar.use_mythical_materials then
        local pind=1
        local allowed_interactions={}
        for sph,_ in pairsByKeys(ropar.mythical_sphere) do
            for k,v in pairsByKeys(interactions.mythical_item_power) do
                if v.spheres[sph] then
                    allowed_interactions[#allowed_interactions+1]=v
                end
            end
        end
        for k,v in ipairs(allowed_interactions) do
            local tok="MYTHICAL_ITEM_POWER_"..k
            tbl[#tbl+1]="[INTERACTION:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl[#tbl+1]="[I_SOURCE:ITEM_POWER]"
            tbl[#tbl+1]="[IS_CDI:INTERACTION:"..tok.."]"
            tbl=table_merge(tbl,v.interaction())
        end
    end
    if debug_level>=1 then
        print_table(tbl)
    end
    raws.register_interactions(tbl)
end

function generate_random_entities()
    local tbl={}
    local l=get_debug_logger()
    l("Starting entitites...")
    for i=1,random_object_parameters.entity_def_number_guardian do
        local tok=random_object_parameters.token_prefix.."GUARDIAN_ENTITY_"..tostring(i)
        local t=generate_from_list(entities.vault_guardian,i,tok)
        local generated_tbl = t and (t.entity or t.raws)
        if generated_tbl then
            tbl[#tbl+1]="[ENTITY:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl[#tbl+1]="[SITE_GUARDIAN]"
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    for i=1,random_object_parameters.entity_def_number_mythical do
        local tok=random_object_parameters.token_prefix.."MYTHICAL_ENTITY_"..tostring(i) -- okay mostly because the above is always prefixed with some HF
        local t=generate_from_list(entities.mythical_guardian,i,tok)
        local generated_tbl = t and (t.entity or t.raws)
        if generated_tbl then
            tbl[#tbl+1]="[ENTITY:"..tok.."]"
            tbl=add_generated_info(tbl)
            tbl[#tbl+1]="[MYTHICAL]"
            tbl[#tbl+1]="[SITE_GUARDIAN]"
            tbl=table_merge(tbl,generated_tbl)
        end
    end
    if debug_level>=1 then
        print_table(tbl)
    end
    raws.register_entities(tbl)
end