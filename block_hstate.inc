      [*] = ;   // === BRIDGE HUMAN STATE: the world as seen from a human slot ===
      [*] = ;   // The per-player Progress tick runs for EVERY player; ProgressAI, and with it
      [*] = ;   // the whole native brain, is started one line above us and only for bai slots
      [*] = ;   // or humans with the adviser on. So on a human slot there is no native AI at
      [*] = ;   // all - and no aidata lists either. Everything here is rebuilt from raw object
      [*] = ;   // scans: that is the price of playing the human side, and the point of it.
      [*] = ;   if (gPlayer[plind].bexists) and (not gPlayer[plind].bai) and
      [*] = ;      (not _net_IsClient) and (not _net_IsReplay) and
      [*] = ;      (gMap.gamestage = gc_map_gamestage_started) then
      [*] = ;   begin
      [*] = ;      var hsnow : Float = GetGameTime;
      [*] = ;      var hshb : Integer = ParserSelectByKey('br_hstate');
      [*] = ;      if (hshb = 0) then
      [*] = ;      hshb := ParserCreate('br_hstate');
      [*] = ;      var hslast : Float = ParserGetFloatValueByKeyByHandle(hshb, 'wrote');
      [*] = ;      // Once per game second is enough: the model thinks every 15-20 seconds, and
      [*] = ;      // a full object scan every frame would be paid for by the simulation.
      [*] = ;      if (hsnow - hslast >= 1.0) or (hsnow < hslast) then
      [*] = ;      begin
      [*] = ;         ParserClearByHandle(hshb);
      [*] = ;         ParserSetFloatValueByKeyByHandle(hshb, 'wrote', hsnow);
      [*] = ;         var hsp : Integer = ParserSelectByKey('br_hp');
      [*] = ;         if (hsp = 0) then
      [*] = ;         hsp := ParserCreate('br_hp');
      [*] = ;         ParserClearByHandle(hsp);
      [*] = ;         var hscid : Integer = gPlayer[plind].cid;
      [*] = ;         var hsph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'plind',    plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'gametime', Round(hsnow));
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'cid',      hscid);
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'human',   gMap.players[plind].bhuman);
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'adviser', gPlayer[plind].playeradviser.adviser.benable);
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'peacemode', gbool_peacemode);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'food',  not gPlayer[plind].res[gc_resource_type_food]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wood',  not gPlayer[plind].res[gc_resource_type_wood]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'stone', not gPlayer[plind].res[gc_resource_type_stone]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'gold',  not gPlayer[plind].res[gc_resource_type_gold]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'iron',  not gPlayer[plind].res[gc_resource_type_iron]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'coal',  not gPlayer[plind].res[gc_resource_type_coal]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_farm',     gPlayer[plind].farm);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_farmused', gPlayer[plind].counter.farmused);
      [*] = ;         // --- one pass over our objects: everything below comes from it ---
      [*] = ;         var hspea, hsidle, hsbuildp, hsunfin : Integer;
      [*] = ;         var hsonf, hsonw, hsons, hsonmine : Integer;
      [*] = ;         var hsinf, hsshoot, hscav, hsfree : Integer;
      [*] = ;         var hscen, hsmill, hssmith, hsba, hsstore, hshouse : Integer;
      [*] = ;         var hsmg, hsmi, hsmc, hstow, hsmark, hsacad : Integer;
      [*] = ;         var hsba18, hsstab : Integer;
      [*] = ;         var hswip : String;
      [*] = ;         var hscx, hscz : Float;
      [*] = ;         var hspeaid : Integer = -1;
      [*] = ;         var hsk : Integer;
      [*] = ;         var hscount : Integer = GetPlayerGameObjectsCountByHandle(hsph);
      [*] = ;         for hsk := 0 to hscount-1 do
      [*] = ;         begin
      [*] = ;            var hsgo : Integer = GetGameObjectHandleByIndex(hsk, hsph);
      [*] = ;            var hspo : Pointer = _unit_GetTObj(hsgo);
      [*] = ;            if (hspo<>nil) then
      [*] = ;            begin
      [*] = ;               var hsuc : Integer = TObj(hspo).cid;
      [*] = ;               var hsui : Integer = TObj(hspo).id;
      [*] = ;               var hsusage : Integer = gObjProp[hsuc][hsui].usage;
      [*] = ;               var hsrole : Integer = gObjProp[hsuc][hsui].airole;
      [*] = ;               if (gObjProp[hsuc][hsui].bbuilding) then
      [*] = ;               begin
      [*] = ;                  // The unfinished count used to be one number, building_now, and the state
      [*] = ;                  // said centers=0 while a town centre already stood as a foundation. The
      [*] = ;                  // model read that as "the order did not go through", invented a cause and
      [*] = ;                  // repeated BUILD tick after tick. Now it sees WHAT is being built and how
      [*] = ;                  // many builders fit around it: gCustomObjPoints[cid,id].builderCount is the
      [*] = ;                  // building geometry and the upper bound for the BUILDERS command. Zero
      [*] = ;                  // means the engine has not computed it yet.
      [*] = ;                  if (not TObj(hspo).bbuilt) then
      [*] = ;                  begin
      [*] = ;                     hsunfin := hsunfin + 1;
      [*] = ;                     var hswn : String = IntToStr(hsrole);
      [*] = ;                     if (hsrole = gc_ai_unit_center) then hswn := 'center';
      [*] = ;                     if (hsrole = gc_ai_unit_mill) then hswn := 'mill';
      [*] = ;                     if (hsrole = gc_ai_unit_smith) then hswn := 'smith';
      [*] = ;                     if (hsrole = gc_ai_unit_ba17) then hswn := 'ba17';
      [*] = ;                     if (hsrole = gc_ai_unit_ba18) then hswn := 'ba18';
      [*] = ;                     if (hsrole = gc_ai_unit_stable) then hswn := 'stable';
      [*] = ;                     if (hsrole = gc_ai_unit_store) then hswn := 'store';
      [*] = ;                     if (hsrole = gc_ai_unit_house) then hswn := 'house';
      [*] = ;                     if (hsrole = gc_ai_unit_tower) then hswn := 'tower';
      [*] = ;                     if (hsrole = gc_ai_unit_market) then hswn := 'market';
      [*] = ;                     if (hsrole = gc_ai_unit_academi) then hswn := 'academi';
      [*] = ;                     if (hsrole = gc_ai_unit_minegold) then hswn := 'minegold';
      [*] = ;                     if (hsrole = gc_ai_unit_mineiron) then hswn := 'mineiron';
      [*] = ;                     if (hsrole = gc_ai_unit_minecoal) then hswn := 'minecoal';
      [*] = ;                     if (hswip <> '') then hswip := hswip + ',';
      [*] = ;                     hswip := hswip + hswn + '/' + IntToStr(gCustomObjPoints[hsuc, hsui].builderCount);
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     if (hsrole = gc_ai_unit_center) then
      [*] = ;                     begin
      [*] = ;                        hscen := hscen + 1;
      [*] = ;                        hscx := GetGameObjectPositionXByHandle(hsgo);
      [*] = ;                        hscz := GetGameObjectPositionZByHandle(hsgo);
      [*] = ;                     end;
      [*] = ;                     if (hsrole = gc_ai_unit_mill)     then hsmill  := hsmill + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_smith)    then hssmith := hssmith + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_ba17)     then hsba    := hsba + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_ba18)     then hsba18 := hsba18 + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_stable)   then hsstab := hsstab + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_store)    then hsstore := hsstore + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_house)    then hshouse := hshouse + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_minegold) then hsmg   := hsmg + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_mineiron) then hsmi   := hsmi + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_minecoal) then hsmc   := hsmc + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_tower)    then hstow  := hstow + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_market)   then hsmark := hsmark + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_academi)  then hsacad := hsacad + 1;
      [*] = ;                  end;
      [*] = ;               end
      [*] = ;               else
      [*] = ;               begin
      [*] = ;                  if (hsusage = gc_obj_usage_peasant) then
      [*] = ;                  begin
      [*] = ;                     hspea := hspea + 1;
      [*] = ;                     hspeaid := hsui;
      [*] = ;                     // What this peasant is actually doing. The first order is the
      [*] = ;                     // current one; a peasant inside a building is in a mine.
      [*] = ;                     var hsot : Integer = TObj(hspo).orders[0].itype;
      [*] = ;                     if (TObj(hspo).insideofuid <> 0) then
      [*] = ;                     hsonmine := hsonmine + 1
      [*] = ;                     else
      [*] = ;                     if (hsot = gc_obj_order_type_build) or (hsot = gc_obj_order_type_repair) then
      [*] = ;                     hsbuildp := hsbuildp + 1
      [*] = ;                     else
      [*] = ;                     if (hsot = gc_obj_order_type_gainres) then
      [*] = ;                     begin
      [*] = ;                        var hstrg : Integer = TObj(hspo).orders[0].info.trg;
      [*] = ;                        var hsres : Pointer = _res_GetTRes(hstrg);
      [*] = ;                        if (hsres<>nil) then
      [*] = ;                        begin
      [*] = ;                           if (TRes(hsres).itype = gc_resource_type_wood)  then hsonw := hsonw + 1;
      [*] = ;                           if (TRes(hsres).itype = gc_resource_type_stone) then hsons := hsons + 1;
      [*] = ;                           if (TRes(hsres).itype = gc_resource_type_food)  then hsonf := hsonf + 1;
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (hsot = gc_obj_order_type_none) then
      [*] = ;                     hsidle := hsidle + 1;
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     if (hsusage = gc_obj_usage_lightinfantry) or (hsusage = gc_obj_usage_weak) or
      [*] = ;                        (hsusage = gc_obj_usage_grenadier) then
      [*] = ;                     hsinf := hsinf + 1;
      [*] = ;                     if (hsusage = gc_obj_usage_shooter) or (hsusage = gc_obj_usage_archer) then
      [*] = ;                     hsshoot := hsshoot + 1;
      [*] = ;                     if (hsusage = gc_obj_usage_fasthorse) or (hsusage = gc_obj_usage_hardhorse) or
      [*] = ;                        (hsusage = gc_obj_usage_horseshooter) then
      [*] = ;                     hscav := hscav + 1;
      [*] = ;                     if (hsusage <> gc_obj_usage_none) and (TObj(hspo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                     hsfree := hsfree + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         // WAVE_SENT: how many were in the LAST wave we sent.
      [*] = ;         //
      [*] = ;         // It was called wave_alive for one run, and that was a lie. The group
      [*] = ;         // the command block fills ('coss3_bridge_wave', block_hcmd:575) does
      [*] = ;         // NOT lose its dead: measured 13.09, the count stayed at 22 through
      [*] = ;         // six ticks and at 23 through four more, changing only when a new
      [*] = ;         // wave replaced the old one (GroupClearGameObjectsByHandle).
      [*] = ;         //
      [*] = ;         // The model believed it. At 9:17 it held back a second wave because
      [*] = ;         // 'the previous one of 23 is still alive' - and it almost certainly
      [*] = ;         // was not. A field that lies is worse than no field: the model is
      [*] = ;         // wrong exactly as far as the description of the world is wrong.
      [*] = ;         //
      [*] = ;         // So the name now says what it measures. How many are still ALIVE is
      [*] = ;         // a different question and needs a different way to count - the group
      [*] = ;         // cannot answer it.
      [*] = ;         var hswg : String = 'coss3_bridge_wave';
      [*] = ;         var hswave : Integer = _misc_GetOrCreateGroupByName(hsph, hswg);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wave_sent',
      [*] = ;                                        GetGroupCountGameObjectsByHandle(hswave));
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'objects',   hscount);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'peasants',  hspea);
      [*] = ;         // No town centre yet means no position, and en_near_dist is measured
      [*] = ;         // from hscx/hscz - without this fallback the distance to the enemy
      [*] = ;         // would be measured from the map corner. Anchor on any object we own.
      [*] = ;         if (hscen = 0) and (hscount > 0) then
      [*] = ;         begin
      [*] = ;            var hsanchor : Integer = GetGameObjectHandleByIndex(0, hsph);
      [*] = ;            hscx := GetGameObjectPositionXByHandle(hsanchor);
      [*] = ;            hscz := GetGameObjectPositionZByHandle(hsanchor);
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_food',   hsonf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_wood',   hsonw);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_stone',  hsons);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_mine',   hsonmine);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_build',  hsbuildp);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'idle_pea',  hsidle);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'centers',   hscen);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mills',     hsmill);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'smiths',    hssmith);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'ba17',      hsba);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'ba18',      hsba18);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'stables',   hsstab);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_stores', hsstore);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'houses',    hshouse);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mines_gold', hsmg);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mines_iron', hsmi);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mines_coal', hsmc);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_towers', hstow);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'markets',   hsmark);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'academies', hsacad);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'building_now', hsunfin);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'wip', hswip);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_inf',      hsinf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_shooters', hsshoot);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_cav',      hscav);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_freewar',   hsfree);
      [*] = ;         ParserSetFloatValueByKeyByHandle(hsp, 'my_x', hscx);
      [*] = ;         ParserSetFloatValueByKeyByHandle(hsp, 'my_z', hscz);
      [*] = ;         // Real prices, straight from the engine. On the AI side this was the one
      [*] = ;         // thing we could never read, and the model spent whole episodes guessing
      [*] = ;         // which resource blocked a hire.
      [*] = ;         if (hspeaid >= 0) then
      [*] = ;         begin
      [*] = ;            var hcf, hcw, hcs, hcg, hci, hcc : Integer;
      [*] = ;            // price[] from the player's object base - see block_human.inc.
      [*] = ;            hcf := gPlayer[plind].objbase[hscid][hspeaid].price[gc_resource_type_food];
      [*] = ;            hcw := gPlayer[plind].objbase[hscid][hspeaid].price[gc_resource_type_wood];
      [*] = ;            hcg := gPlayer[plind].objbase[hscid][hspeaid].price[gc_resource_type_gold];
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'pea_food', hcf);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'pea_wood', hcw);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'pea_gold', hcg);
      [*] = ;            ParserSetBoolValueByKeyByHandle(hsp, 'cost_ok', True);
      [*] = ;         end
      [*] = ;         else
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'cost_ok', False);
      [*] = ;         // --- enemies: who they are and how many peasants they still have ---
      [*] = ;         var hspl, hsbest : Integer;
      [*] = ;         var hsbestd : Float = 1000000;
      [*] = ;         hsbest := -1;
      [*] = ;         for hspl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;         if (gPlayer[hspl].bexists) and (hspl <> plind) then
      [*] = ;         begin
      [*] = ;            var hsenemy : Boolean = ((gPlayer[plind].enemyPlMask and gPlayer[hspl].myPlMask) <> 0);
      [*] = ;            ParserSetBoolValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_enemy', hsenemy);
      [*] = ;            var hseph : Integer = GetPlayerHandleByIndex(hspl);
      [*] = ;            var hsec : Integer = GetPlayerGameObjectsCountByHandle(hseph);
      [*] = ;            var hsepea, hsebld, hsj : Integer;
      [*] = ;            for hsj := 0 to hsec-1 do
      [*] = ;            begin
      [*] = ;               var hseg : Integer = GetGameObjectHandleByIndex(hsj, hseph);
      [*] = ;               var hsep : Pointer = _unit_GetTObj(hseg);
      [*] = ;               if (hsep<>nil) then
      [*] = ;               begin
      [*] = ;                  if (gObjProp[TObj(hsep).cid][TObj(hsep).id].usage = gc_obj_usage_peasant) then
      [*] = ;                  hsepea := hsepea + 1;
      [*] = ;                  if (gObjProp[TObj(hsep).cid][TObj(hsep).id].bbuilding) then
      [*] = ;                  begin
      [*] = ;                     hsebld := hsebld + 1;
      [*] = ;                     if (hsenemy) and (hscen > 0) then
      [*] = ;                     begin
      [*] = ;                        var hsd : Float = VectorDistance(GetGameObjectPositionXByHandle(hseg), 0,
      [*] = ;                             GetGameObjectPositionZByHandle(hseg), hscx, 0, hscz);
      [*] = ;                        if (hsd < hsbestd) then
      [*] = ;                        begin
      [*] = ;                           hsbestd := hsd;
      [*] = ;                           hsbest := hspl;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_peasants', hsepea);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_bldgs',    hsebld);
      [*] = ;         end;
      [*] = ;         if (hsbest >= 0) then
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'en_near_dist', Round(hsbestd));
      [*] = ;         // Open map? additional.balloon = 2 hands the balloon to everyone
      [*] = ;         // and turns the fog of war off for all (_player_UpdateFOW,
      [*] = ;         // player.script:456). It decides what the bridge may honestly
      [*] = ;         // tell the model about the enemy: with an open map a human sees
      [*] = ;         // his base and his troops too, so the numbers are not a head start.
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'map_open',
      [*] = ;              (gMap.settings.additional.balloon = gc_mapsettings_balloon_with));
      [*] = ;         // Why the last command failed, put there by the command block. It is
      [*] = ;         // NOT cleared here: the state is written every game second while the
      [*] = ;         // model looks once in fifteen, and clearing on write would hide the
      [*] = ;         // answer from the only reader who needs it. The command block clears it
      [*] = ;         // when a new batch arrives.
      [*] = ;         var hsfl : Integer = ParserSelectByKey('br_hfail');
      [*] = ;         if (hsfl <> 0) then
      [*] = ;         begin
      [*] = ;            var hswhy : String = ParserGetValueByKeyByHandle(hsfl, 'why');
      [*] = ;            if (StrLength(hswhy) > 0) then
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'last_fail', hswhy);
      [*] = ;         end;
      [*] = ;         // Upgrades THIS NATION actually has. The list in SYSTEM was the same
      [*] = ;         // for every nation, and that is a lie: the sets differ. On 13.09 the
      [*] = ;         // model ordered 'reaper' with a mill standing and got back
      [*] = ;         // 'no upgrade with this name for our nation' - a tick spent on
      [*] = ;         // something that does not exist.
      [*] = ;         //
      [*] = ;         // We export SUFFIXES because that is what the UPGRADE command takes:
      [*] = ;         // an upgrade sid is nation prefix plus base name ('engmilfood140'),
      [*] = ;         // and the command block matches by suffix. The first three letters
      [*] = ;         // are the nation, so they are cut off. Comma separated, ready to be
      [*] = ;         // shown to the model as is.
      [*] = ;         var hsupg : String;
      [*] = ;         var hsui : Integer;
      [*] = ;         for hsui := 0 to gc_country_maxupgradecount-1 do
      [*] = ;         begin
      [*] = ;            var hsus : String = gCountry[hscid].upgrade[hsui].id;
      [*] = ;            if (StrLength(hsus) > 3) then
      [*] = ;            begin
      [*] = ;               if (StrLength(hsupg) > 0) then
      [*] = ;               hsupg := hsupg + ',';
      [*] = ;               hsupg := hsupg + SubStr(hsus, 4, StrLength(hsus)-3);
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'upg_avail', hsupg);
      [*] = ;         // How the match ended, in the same file the policy already reads every
      [*] = ;         // tick. The engine pauses the simulation the moment it sets victorystate,
      [*] = ;         // so this block is about to freeze - and this is the last line it writes.
      [*] = ;         // Without it the trace simply stopped and the policy had to guess between
      [*] = ;         // 'window minimized', 'match over' and 'MODE 1 broke it'.
      [*] = ;         var hsvic : String = 'none';
      [*] = ;         if (gPlayer[plind].victorystate = gc_player_victorystate_win) then
      [*] = ;         hsvic := 'win'
      [*] = ;         else
      [*] = ;         if (gPlayer[plind].victorystate = gc_player_victorystate_lose) then
      [*] = ;         hsvic := 'lose';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'victory', hsvic);
      [*] = ;         ParserSaveToFileByHandle(hsp, '@@OUT@@coss3_eco_P' + IntToStr(plind) + '.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE HUMAN STATE ===