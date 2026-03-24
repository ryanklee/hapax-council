function pairsByKeys (t, f)
    local a = {}
    for n in pairs(t) do table.insert(a, n) end
    table.sort(a, f)
    local i = 0
    local iter = function ()
        i = i + 1
        if a[i] == nil then return nil
        else return a[i], t[a[i]]
        end
    end
    return iter
end

function pick_random(t)
    if t and #t>0 then
        return t[trandom(#t)+1]
    else
        return nil
    end
end

function pick_random_no_replace(t)
    if t and #t>0 then
        return table.remove(t,trandom(#t)+1)
    else
        return nil
    end
end

function pick_random_conditional(t,cond,...)
    local is_fun=type(cond)=="function"
    local candidates={}
    -- we use pairsByKeys so the RNG seed is stable
    for k,v in pairsByKeys(t) do
        if is_fun then 
            if cond(k,v,...) then
                candidates[#candidates+1]=v
            end
        elseif v[cond](...) then
            candidates[#candidates+1]=v
        end
    end
    return pick_random(candidates)
end

function pick_random_conditional_pairs(t,cond,...)
    local is_fun=type(cond)=="function"
    local candidates={}
    -- we use pairsByKeys so the RNG seed is stable
    for k,v in pairsByKeys(t) do
        if is_fun then 
            if cond(k,v,...) then
                candidates[#candidates+1]=k
            end
        elseif v[cond](...) then
            candidates[#candidates+1]=k
        end
    end
    return pick_random(candidates)
end

function one_in(x)
    return type(x)=="number" and x>0 and trandom(math.floor(x))==0
end

function split_to_lines(tbl,str)
    for s in string.gmatch(str,"[^\r\n]+") do
        tbl[#tbl+1]=s
    end
    return tbl
end

function map_merge(tbl1,tbl2)
    if not (type(tbl1)=='table' and type(tbl2)=='table') then return tbl1 end
    for k,v in pairs(tbl2) do
        tbl1[k]=tbl1[k] or v
    end
    return tbl1
end

function table_merge(tbl1,tbl2)
    if not (type(tbl1)=='table' and type(tbl2)=='table') then return tbl1 end
    for k,v in ipairs(tbl2) do
        tbl1[#tbl1+1]=v
    end
    return tbl1
end

function find_in_array_part(tbl,item)
    for k,v in ipairs(tbl) do
        if v==item then return true end
    end
    return false
end

function convert_array_to_set(tbl)
    for k,v in ipairs(tbl) do
        tbl[v]=true
    end
end

function add_unique(tbl,item)
    if not find_in_array_part(tbl,item) then
        tbl[#tbl+1]=item
        return true
    end
    return false
end

function remove_item(tbl,item)
    for i=#tbl,1,-1 do
        if tbl[i]==item then table.remove(tbl,i) end
    end
end

function pick_random_pairs(tbl)
    if not tbl then return nil end
    local cand={}
    -- we use pairsByKeys so the RNG seed is stable
    for k,v in pairsByKeys(tbl) do
        if v then cand[#cand+1]=k end
    end
    return pick_random(cand)
end

function pick_random_pairs_with_sort(tbl,f)
    if not tbl then return nil end
    local cand={}
    -- we use pairsByKeys so the RNG seed is stable
    for k,v in pairsByKeys(tbl,f) do
        if v then cand[#cand+1]=k end
    end
    return pick_random(cand)
end

function log(...)
    local s=""
    local args=table.pack(...)
    for i=1,args.n do
        s=s..tostring(args[i]).." "
    end
    lua_log(s)
end

--------------------------
debug_level=0

function get_caller_loc_string()
    local info = debug.getinfo(3)
    return info.source..":"..info.currentline
end


function get_debug_logger(level)
    level=level or 1
    if debug_level>=level then
        local count=0
        return function(...)
            log(count,get_caller_loc_string(),...)
            count=count+1
        end
    else
        return function() end
    end
end

function partial_function(f,arg)
    return function(...) return f(arg,...) end
end

function pick_weighted_from_table(tbl)
    -- we assume this table is sorted for RNG stability before the call since pairsByKeys doesn't sort arrays
    local l=get_debug_logger(4)
    local o=get_debug_logger(-10)
    l("Picking weighted table at ",get_caller_loc_string)
    local total_weight=0
    for k,v in pairs(tbl) do
        l(k,v,v.weight)
        if not v.weight then
            o("A table that should have a weight does not. Spewing contents of table below.")
            print_table(v)
        end
        total_weight=total_weight+(v.weight or 1)
    end
    local roll=trandom(total_weight)
    l("Roll:",roll)
    for i=1,10 do
        for k,v in pairs(tbl) do
            l(k,v.weight,roll)
            roll=roll-v.weight
            if roll<=0 then return v end
        end
    end
    return nil
end

function log_table(tbl,debug_level,nest_level,added_debug_from_nest)
    if type(tbl) ~= "table" then return end
    if not nest_level then nest_level=0 end
    if not added_debug_from_nest then added_debug_from_nest=0 end
    local f = get_debug_logger(debug_level+nest_level*added_debug_from_nest)
    local already_printed={}
    local open_str = '|'
    open_str = open_str..string.rep('-',nest_level)
    open_str = open_str..'>'
    for k,v in pairs(tbl) do
        f(open_str,k,v)
        already_printed[k]=true
        log_table(v,debug_level,nest_level+1,added_debug_from_nest)
    end
    for k,v in ipairs(tbl) do
        if not already_printed[k] then
            f(open_str,k,v)
            log_table(v,debug_level,nest_level+1,added_debug_from_nest)
        end
    end
end

function print_table(tbl,nest_level)
    if type(tbl) ~= "table" then return end
    if not nest_level then nest_level=0 end
    local already_printed={}
    local open_str = '|'
    open_str = open_str..string.rep('-',nest_level)
    open_str = open_str..'>'
    for k,v in pairs(tbl) do
        log(open_str,k,v)
        already_printed[k]=true
        print_table(v,nest_level+1)
    end
    for k,v in ipairs(tbl) do
        if not already_printed[k] then
            log(open_str,k,v)
            print_table(v,nest_level+1)
        end
    end
end

function shallow_copy(tbl)
    if type(tbl) ~= "table" then return tbl end
    local ret={}
    for k,v in pairs(tbl) do
        ret[k]=v
    end
    return ret
end

function deep_copy(tbl)
    if type(tbl) ~= "table" then return tbl end
    local ret={}
    for k,v in pairs(tbl) do
        ret[k]=deep_copy(v)
    end
    return ret
end

function generate_from_list(tbl,...)
    local results={}
    local total_weight=0
    local o=get_debug_logger(-10)
    -- we use pairsByKeys so the RNG seed is stable
    for k,v in pairsByKeys(tbl) do
        local result = v(...)
        if result then
            if not result.weight then
                o("A table that should have a weight does not. Spewing contents of table below.")
                print_table(result)
            end
            total_weight = total_weight + (result.weight or 1)
            results[#results+1]=result
        end
    end
    local roll = trandom(math.ceil(total_weight))+1
    for i=1,10 do -- We're probably not going to do it even twice, but it's fine
        for k,v in ipairs(results) do
            roll = roll - v.weight
            if roll<=0 then 
                return v
            end
        end
    end
    return results[1] or nil
end

evil_spheres = {
    "BLIGHT",
    "CHAOS",
    "DEATH",
    "DEFORMITY",
    "DEPRAVITY",
    "DISEASE",
    "JEALOUSY",
    "LIES",
    "MISERY",
    "MURDER",
    "NIGHTMARES",
    "SUICIDE",
    "THEFT",
    "THRALLDOM",
    "TORTURE",
    "TREACHERY",
}

good_spheres = {
"CHARITY",
"CONSOLATION",
"FORGIVENESS",
"FREEDOM",
"GENEROSITY",
"HAPPINESS",
"HEALING",
"HOSPITALITY",
"LOVE",
"MERCY",
"PEACE",
"REVELRY",
"SACRIFICE",
"TRUTH",
"WISDOM",
}

-- mods can add more
random_sphere_adjective={
    AGRICULTURE={"agricultural"},
    ANIMALS={"animal"},
    ART={"artistic"},
    BALANCE={"balanced"},
    BEAUTY={"beautiful"},
    BIRTH={"birthing"},
    BLIGHT={"blighted"},
    BOUNDARIES={"delineated"},
    CAVERNS={"cavernous"},
    CHAOS={"chaotic"},
    CHARITY={"charitable"},
    CHILDREN={"child-like"},
    COASTS={"coastal"},
    CONSOLATION={"consoling"},
    COURAGE={"courageous"},
    CRAFTS={"crafted"},
    CREATION={"created"},
    DANCE={"dancing"},
    DARKNESS={"dark"},
    DAWN={"dawning"},
    DAY={"noon-time"},
    DEATH={"dead"},
    DEFORMITY={"deformed"},
    DEPRAVITY={"depraved"},
    DISCIPLINE={"disciplined"},
    DISEASE={"diseased"},
    DREAMS={"dreaming"},
    DUSK={"dusklight"},
    DUTY={"dutiful"},
    EARTH={"earthen"},
    FAMILY={"familial"},
    FAME={"famous"},
    FATE={"fated"},
    FERTILITY={"fertile"},
    FESTIVALS={"festive"},
    FIRE={"fiery"},
    FISH={"fish"},
    FISHING={"fish"},
    FOOD={"baked"},
    FORGIVENESS={"forgiving"},
    FORTRESSES={"protected"},
    FREEDOM={"free"},
    GAMBLING={"gambling"},
    GAMES={"playful"},
    GENEROSITY={"generous"},
    HAPPINESS={"happy"},
    HEALING={"healing"},
    HOSPITALITY={"hospitable"},
    HUNTING={"hunting"},
    INSPIRATION={"inspired"},
    JEALOUSY={"jealous"},
    JEWELS={"jeweled"},
    JUSTICE={"just"},
    LABOR={"laboring"},
    LAKES={"wet"},
    LAWS={"rigid"},
    LIES={"deceitful"},
    LIGHT={"shining"},
    LIGHTNING={"electrical"},
    LONGEVITY={"long-lived"},
    LOVE={"loving"},
    LOYALTY={"loyal"},
    LUCK={"lucky"},
    LUST={"lustful"},
    MARRIAGE={"married"},
    MERCY={"merciful"},
    METALS={"metal"},
    MINERALS={"crystal"},
    MISERY={"miserable"},
    MIST={"misty"},
    MOON={"moonlit"},
    MOUNTAINS={"mountainous"},
    MUCK={"muddy"},
    MURDER={"murderous"},
    MUSIC={"lyrical"},
    NATURE={"natural"},
    NIGHT={"dark"},
    NIGHTMARES={"nightmarish"},
    OATHS={"sworn"},
    OCEANS={"oceanic"},
    ORDER={"ordered"},
    PAINTING={"painted"},
    PEACE={"peaceful"},
    PERSUASION={"persuasive"},
    PLANTS={"leafy"},
    POETRY={"poetic"},
    PREGNANCY={"pregnant"},
    RAIN={"rainy"},
    RAINBOWS={"colorful"},
    REBIRTH={"reborn"},
    REVELRY={"joyous"},
    REVENGE={"vengeful"},
    RIVERS={"flowing"},
    RULERSHIP={"lordly"},
    RUMORS={"whispering"},
    SACRIFICE={"sacrificial"},
    SALT={"salty"},
    SCHOLARSHIP={"scholarly"},
    SEASONS={"seasonal"},
    SILENCE={"silent"},
    SKY={"cloudy"},
    SONG={"singing"},
    SPEECH={"wordy"},
    STARS={"starry"},
    STORMS={"stormy"},
    STRENGTH={"strong"},
    SUICIDE={"hopeless"},
    SUN={"sunny"},
    THEFT={"thieving"},
    THRALLDOM={"enslaved"},
    THUNDER={"thunderous"},
    TORTURE={"wicked"},
    TRADE={"enterprising"},
    TRAVELERS={"traveling"},
    TREACHERY={"treacherous"},
    TREES={"wooden"},
    TRICKERY={"tricky"},
    TRUTH={"true"},
    TWILIGHT={"twilight"},
    VALOR={"valorous"},
    VICTORY={"victorious"},
    VOLCANOS={"volcanic"},
    WAR={"warring"},
    WATER={"watery"},
    WEALTH={"wealthy"},
    WEATHER={"stormy"},
    WIND={"windy"},
    WISDOM={"wise"},
    WRITING={"lettered"},
    YOUTH={"young"},
}

function get_random_sphere_adjective(sph)
    return sph and pick_random(random_sphere_adjective[sph]) or "no sphere"
end

-- structure's a bit of a mess, but one can e.g. do
-- random_sphere_nouns.AGRICULTURE[#random_sphere_nouns.AGRICULTURE+1]={str="agriculture"}
-- which is hopefully good
random_sphere_nouns={
    AGRICULTURE={{str="farming"}},
    ANIMALS={{str="animals",flags={OF=true}}},
    ART={{str="art"}},
    BALANCE={{str="balance"}},
    BEAUTY={{str="beauty"}},
    BIRTH={{str="birth"}},
    BLIGHT={{str="blight"}},
    BOUNDARIES={{str="boundaries",flags={OF=true}}},
    CAVERNS={{str="caverns",flags={OF=true}}},
    CHAOS={{str="chaos"}},
    CHARITY={{str="charity"}},
    CHILDREN={{str="children",flags={OF=true}}},
    COASTS={{str="coasts",flags={OF=true}}},
    CONSOLATION={{str="consolation",flags={OF=true}}},
    COURAGE={{str="courage"}},
    CRAFTS={{str="crafts",flags={OF=true}}},
    CREATION={{str="creation"}},
    DANCE={{str="dance"}},
    DARKNESS={{str="darkness"}},
    DAWN={{str="dawn"}},
    DAY={{str="day"}},
    DEATH={{str="death"}},
    DEFORMITY={{str="deformity",flags={OF=true}}},
    DEPRAVITY={{str="depravity",flags={OF=true}}},
    DISCIPLINE={{str="discipline",flags={OF=true}}},
    DISEASE={{str="disease"}},
    DREAMS={{str="dreams",flags={OF=true}}},
    DUSK={{str="dusk"}},
    DUTY={{str="duty"}},
    EARTH={{str="earth"}},
    FAMILY={{str="family"}},
    FAME={{str="fame"}},
    FATE={{str="fate"}},
    FERTILITY={{str="fertility",flags={OF=true}}},
    FESTIVALS={{str="festivals",flags={OF=true}}},
    FIRE={{str="fire"}},
    FISH={{str="fish",flags={OF=true}}},
    FISHING={{str="fishing"}},
    FOOD={{str="food"}},
    FORGIVENESS={{str="forgiveness",flags={OF=true}}},
    FORTRESSES={{str="fortresses",flags={OF=true}}},
    FREEDOM={{str="freedom"}},
    GAMBLING={{str="gambling"}},
    GAMES={{str="games",flags={OF=true}}},
    GENEROSITY={{str="generosity",flags={OF=true}}},
    HAPPINESS={{str="happiness",flags={PRE=true,OF=true}}},
    HEALING={{str="healing"}},
    HOSPITALITY={{str="hospitality",flags={OF=true}}},
    HUNTING={{str="hunting"}},
    INSPIRATION={{str="inspiration",flags={OF=true}}},
    JEALOUSY={{str="jealousy",flags={OF=true}}},
    JEWELS={{str="jewels",flags={OF=true}}},
    JUSTICE={{str="justice"}},
    LABOR={{str="labor"}},
    LAKES={{str="lakes",flags={OF=true}}},
    LAWS={{str="laws",flags={OF=true}}},
    LIES={{str="lies",flags={OF=true}}},
    LIGHT={{str="light"}},
    LIGHTNING={{str="lightning"}},
    LONGEVITY={{str="longevity",flags={OF=true}}},
    LOVE={{str="love"}},
    LOYALTY={{str="loyalty",flags={OF=true}}},
    LUCK={{str="luck"}},
    LUST={{str="lust"}},
    MARRIAGE={{str="marriage"}},
    MERCY={{str="mercy"}},
    METALS={{str="metals",flags={OF=true}}},
    MINERALS={{str="minerals",flags={OF=true}}},
    MISERY={{str="misery"}},
    MIST={{str="mist"}},
    MOON={{str="moon"}},
    MOUNTAINS={{str="mountains",flags={OF=true}}},
    MUCK={{str="muck"}},
    MURDER={{str="murder"}},
    MUSIC={{str="music"}},
    NATURE={{str="nature"}},
    NIGHT={{str="night"}},
    NIGHTMARES={{str="nightmares",flags={OF=true}}},
    OATHS={{str="oaths",flags={OF=true}}},
    OCEANS={{str="oceans",flags={OF=true}}},
    ORDER={{str="order"}},
    PAINTING={{str="painting"}},
    PEACE={{str="peace"}},
    PERSUASION={{str="persuasion",flags={OF=true}}},
    PLANTS={{str="plants",flags={OF=true}}},
    POETRY={{str="poetry"}},
    PREGNANCY={{str="pregnancy"}},
    RAIN={{str="rain"}},
    RAINBOWS={{str="rainbows",flags={OF=true}}},
    REBIRTH={{str="rebirth"}},
    REVELRY={{str="revelry"}},
    REVENGE={{str="revenge"}},
    RIVERS={{str="rivers",flags={OF=true}}},
    RULERSHIP={{str="rulership"}},
    RUMORS={{str="rumors",flags={OF=true}}},
    SACRIFICE={{str="sacrifice"}},
    SALT={{str="salt"}},
    SCHOLARSHIP={{str="scholarship",flags={OF=true}}},
    SEASONS={{str="seasons",flags={OF=true}}},
    SILENCE={{str="silence"}},
    SKY={{str="sky"}},
    SONG={{str="song"}},
    SPEECH={{str="speech"}},
    STARS={{str="stars",flags={OF=true}}},
    STORMS={{str="storms",flags={OF=true}}},
    STRENGTH={{str="strength"}},
    SUICIDE={{str="suicide"}},
    SUN={{str="sun"}},
    THEFT={{str="theft"}},
    THRALLDOM={{str="thralldom",flags={OF=true}}},
    THUNDER={{str="thunder"}},
    TORTURE={{str="torture"}},
    TRADE={{str="trade"}},
    TRAVELERS={{str="travelers",flags={OF=true}}},
    TREACHERY={{str="treachery"}},
    TREES={{str="trees",flags={OF=true}}},
    TRICKERY={{str="trickery"}},
    TRUTH={{str="truth"}},
    TWILIGHT={{str="twilight"}},
    VALOR={{str="valor"}},
    VICTORY={{str="victory"}},
    VOLCANOS={{str="volcanos",flags={OF=true}}},
    WAR={{str="war"}},
    WATER={{str="water"}},
    WEALTH={{str="wealth"}},
    WEATHER={{str="weather"}},
    WIND={{str="wind"}},
    WISDOM={{str="wisdom"}},
    WRITING={{str="writing"}},
    YOUTH={{str="youth"}},
}

function get_random_sphere_noun(sph)
    local tbl = sph and pick_random(random_sphere_nouns[sph]) or {str="no sphere"}
    tbl.flags=tbl.flags or {OF=true,PREPOS=true,PRE=true}
    return tbl
end

function add_sphere_mpp(sphere_list, new_s, available_sphere, available_sphere_cur)
    sphere_list[new_s]=true

    available_sphere[new_s]=false
    available_sphere_cur[new_s]=false
    local total={}
    local l=get_debug_logger(2)
    local function merge_parents(s)
        l("Merging parents",s)
        for k,v in pairs(world.spheres[s].parents) do
            if not total[k] then
                total[k]=v
                merge_parents(k)
            end
        end
    end
    local function merge_children(s)
        l("Merging children",s)
        for k,v in pairs(world.spheres[s].children) do
            if not total[k] then
                total[k]=v
                merge_children(k)
            end
        end
    end
    merge_parents(new_s)
    merge_children(new_s)
    for k,v in pairs(total) do
        available_sphere[k]=false
        available_sphere_cur[k]=false
    end
    for k,v in pairs(world.spheres[new_s].enemies) do
        available_sphere_cur[k]=false
    end
    l("Done with MPP")
end