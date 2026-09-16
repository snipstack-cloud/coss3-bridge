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
      [*] = ;         // Mines split by kind. on_mine was one number for gold, iron and coal
      [*] = ;         // together, and a human sees each mine separately - how many work it and
      [*] = ;         // how many places are left. 15.09: BALANCE gold was issued 3 times in 6
      [*] = ;         // games and nothing observable happened, because nobody could see where
      [*] = ;         // the miners actually were.
      [*] = ;         var hsong, hsoni, hsonc : Integer;
      [*] = ;         var hscapg, hscapi, hscapc : Integer;
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
      [*] = ;                     // How many ACTUALLY build it and how far it has come. A player sees
      [*] = ;                     // both: he counts the workers around the site with his eyes, and the
      [*] = ;                     // bar shows readiness - for an unfinished building that bar IS hp
      [*] = ;                     // growing to maxhp, which is how the engine itself decides that more
      [*] = ;                     // building is possible (hp < maxhp, menu.inc/doupdatecursor.inc:93).
      [*] = ;                     // Without these two numbers the model could not learn what one extra
      [*] = ;                     // builder is worth.
      [*] = ;                     var hsbcnt : Integer = 0;
      [*] = ;                     var hsbuid : Integer = GetGameObjectUniqueIdByHandle(hsgo);
      [*] = ;                     var hsbk : Integer;
      [*] = ;                     for hsbk := 0 to hscount-1 do
      [*] = ;                     begin
      [*] = ;                        var hsbgo : Integer = GetGameObjectHandleByIndex(hsbk, hsph);
      [*] = ;                        var hsbpo : Pointer = _unit_GetTObj(hsbgo);
      [*] = ;                        if (hsbpo<>nil) then
      [*] = ;                        if (gObjProp[TObj(hsbpo).cid][TObj(hsbpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        begin
      [*] = ;                           var hsbot : Integer = TObj(hsbpo).orders[0].itype;
      [*] = ;                           if (hsbot = gc_obj_order_type_build) or (hsbot = gc_obj_order_type_repair) then
      [*] = ;                           begin
      [*] = ;                              // The order target comes as a handle in some paths and as a
      [*] = ;                              // unique id in others - compare with both instead of guessing.
      [*] = ;                              var hsbtrg : Integer = TObj(hsbpo).orders[0].info.trg;
      [*] = ;                              if (hsbtrg = hsgo) or (hsbtrg = hsbuid) then
      [*] = ;                              hsbcnt := hsbcnt + 1;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     var hspct : Integer = 0;
      [*] = ;                     var hsmax : Integer = gPlayer[plind].objbase[hsuc][hsui].maxhp;
      [*] = ;                     if (hsmax > 0) then
      [*] = ;                     hspct := Round((TObj(hspo).hp * 100) / hsmax);
      [*] = ;                     if (hswip <> '') then hswip := hswip + ',';
      [*] = ;                     hswip := hswip + hswn + '/' + IntToStr(gCustomObjPoints[hsuc, hsui].builderCount) +
      [*] = ;                          '/' + IntToStr(hsbcnt) + '/' + IntToStr(hspct);
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
      [*] = ;                     // How many peasants the mine HOLDS: the same sum the engine
      [*] = ;                     // uses in _ai_FillMines (progresseconomicai.inc:1315). An
      [*] = ;                     // upgrade adds places through individual.addpeasantabsorber.
      [*] = ;                     var hscap : Integer = gObjProp[hsuc][hsui].peasantabsorber + TObj(hspo).individual.addpeasantabsorber;
      [*] = ;                     if (hsrole = gc_ai_unit_minegold) then hscapg := hscapg + hscap;
      [*] = ;                     if (hsrole = gc_ai_unit_mineiron) then hscapi := hscapi + hscap;
      [*] = ;                     if (hsrole = gc_ai_unit_minecoal) then hscapc := hscapc + hscap;
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
      [*] = ;                     begin
      [*] = ;                        hsonmine := hsonmine + 1;
      [*] = ;                        // Which mine he is in. insideofuid is a UNIQUE id, not a
      [*] = ;                        // handle: the engine resolves it with
      [*] = ;                        // GetGameObjectHandleByUniqueId (misc/projectile.inc).
      [*] = ;                        var hsinh : Integer = GetGameObjectHandleByUniqueId(TObj(hspo).insideofuid);
      [*] = ;                        var hsinp : Pointer = _unit_GetTObj(hsinh);
      [*] = ;                        if (hsinp<>nil) then
      [*] = ;                        begin
      [*] = ;                           var hsinr : Integer = gObjProp[TObj(hsinp).cid][TObj(hsinp).id].airole;
      [*] = ;                           if (hsinr = gc_ai_unit_minegold) then hsong := hsong + 1;
      [*] = ;                           if (hsinr = gc_ai_unit_mineiron) then hsoni := hsoni + 1;
      [*] = ;                           if (hsinr = gc_ai_unit_minecoal) then hsonc := hsonc + 1;
      [*] = ;                        end;
      [*] = ;                     end
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
      [*] = ;         // --- WHAT BECAME OF THE WAVE -----------------------------------
      [*] = ;         //
      [*] = ;         // 18 games, 1139 men sent in waves, ZERO enemy peasants killed - and
      [*] = ;         // the trace could not tell 'died on the way' from 'arrived and failed'.
      [*] = ;         // wave_sent says how many LEFT; nothing said what happened next. The
      [*] = ;         // model kept guessing: 'maybe the wave is still walking'.
      [*] = ;         //
      [*] = ;         // Only OUR OWN troops, and only what a player sees anyway: he watches
      [*] = ;         // his army on the map, and the game itself shouts 'your troops are
      [*] = ;         // under attack'. Wounded = attacked; far from the centre = marching.
      [*] = ;         //
      [*] = ;         // A SECOND pass on purpose: hscx/hscz (our centre) is only final after
      [*] = ;         // the first loop - a soldier met before the town centre would have been
      [*] = ;         // measured from 0,0.
      [*] = ;         var hswaway : Integer = 0;   // soldiers further than 60 from our centre
      [*] = ;         var hswnear : Integer = 0;   // and how close the NEAREST of them is
      [*] = ;         var hswsx   : Float = 0;     // sum of dx of those away - gives the side
      [*] = ;         var hswsz   : Float = 0;     // sum of dz; sign of the sum is the sign of the mean
      [*] = ;         var hswside : String = '';   // N/S/E/W, as for ore deposits
      [*] = ;         var hswhurt : Integer = 0;   // soldiers with hp below max - being hit
      [*] = ;         var hswfar  : Integer = 0;   // how far the furthest one got
      [*] = ;         if (hscen > 0) then
      [*] = ;         begin
      [*] = ;            var hswi : Integer;
      [*] = ;            for hswi := 0 to hscount-1 do
      [*] = ;            begin
      [*] = ;               var hswh : Integer = GetGameObjectHandleByIndex(hswi, hsph);
      [*] = ;               var hswo : Pointer = _unit_GetTObj(hswh);
      [*] = ;               if (hswo<>nil) then
      [*] = ;               begin
      [*] = ;                  var hswu : Integer = gObjProp[TObj(hswo).cid][TObj(hswo).id].usage;
      [*] = ;                  if (hswu = gc_obj_usage_lightinfantry) or (hswu = gc_obj_usage_weak) or
      [*] = ;                     (hswu = gc_obj_usage_grenadier) or (hswu = gc_obj_usage_shooter) or
      [*] = ;                     (hswu = gc_obj_usage_archer) then
      [*] = ;                  begin
      [*] = ;                     var hswd : Integer = Round(VectorDistance(
      [*] = ;                        GetGameObjectPositionXByHandle(hswh), 0,
      [*] = ;                        GetGameObjectPositionZByHandle(hswh), hscx, 0, hscz));
      [*] = ;                     if (hswd > 60) then
      [*] = ;                     begin
      [*] = ;                        hswaway := hswaway + 1;
      [*] = ;                        if (hswnear = 0) or (hswd < hswnear) then
      [*] = ;                        hswnear := hswd;
      [*] = ;                        hswsx := hswsx + (GetGameObjectPositionXByHandle(hswh) - hscx);
      [*] = ;                        hswsz := hswsz + (GetGameObjectPositionZByHandle(hswh) - hscz);
      [*] = ;                     end;
      [*] = ;                     if (hswd > hswfar) then
      [*] = ;                     hswfar := hswd;
      [*] = ;                     if (TObj(hswo).hp < gPlayer[plind].objbase[TObj(hswo).cid][TObj(hswo).id].maxhp) then
      [*] = ;                     hswhurt := hswhurt + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         // Side as a word, exactly as for ore above: a human reads the minimap.
      [*] = ;         // The SUM is enough - its sign is the sign of the mean, and no division.
      [*] = ;         if (hswaway > 0) then
      [*] = ;         begin
      [*] = ;            if (hswsz < -0.5*Abs(hswsx)) then hswside := 'N';
      [*] = ;            if (hswsz >  0.5*Abs(hswsx)) then hswside := 'S';
      [*] = ;            if (hswsx >  0.5*Abs(hswsz)) then hswside := hswside + 'E';
      [*] = ;            if (hswsx < -0.5*Abs(hswsz)) then hswside := hswside + 'W';
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_away', hswaway);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_near', hswnear);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'mil_side', hswside);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_hurt', hswhurt);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_far',  hswfar);
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
      [*] = ;         // We read exactly what block_hcmd writes when a wave leaves. Before,
      [*] = ;         // this counted the group 'coss3_bridge_wave', but since 14.09 waves go
      [*] = ;         // into coss3_wave_0..7 - the old group is empty forever, so wave_sent
      [*] = ;         // lied zero in every run since, and the model was told 'no waves' right
      [*] = ;         // after sending one. Writer and reader must name the same thing.
      [*] = ;         var hswp : Integer = ParserSelectByKey('br_hwave');
      [*] = ;         var hswave : Integer = 0;
      [*] = ;         if (hswp <> 0) then
      [*] = ;         hswave := ParserGetIntValueByKeyByHandle(hswp, 'sent');
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wave_sent', hswave);
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_gold',   hsong);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_iron',   hsoni);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_coal',   hsonc);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'cap_gold',  hscapg);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'cap_iron',  hscapi);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'cap_coal',  hscapc);
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
      [*] = ;         // --- WHICH FIGHTERS THIS NATION CAN HIRE ----------------------------
      [*] = ;         //
      [*] = ;         // A newcomer opens the barracks and reads what is inside: name, price,
      [*] = ;         // health. The bot never had that. Result, 12 games of 14.09: the army was
      [*] = ;         // made of pikemen ONLY (infantry17 ordered 144 times, musk17 zero times),
      [*] = ;         // and every wave died at the enemy base without killing a single peasant.
      [*] = ;         // musketeernet was available all along - she simply could not see it.
      [*] = ;         //
      [*] = ;         // No aiforce here on purpose: that number lives inside the AI and a human
      [*] = ;         // never sees it. Price and health he does see, by clicking the unit.
      [*] = ;         var hsfr : array [0..4] of Integer;
      [*] = ;         var hsfn : array [0..4] of String;
      [*] = ;         hsfr[0] := gc_ai_unit_infantry17;  hsfn[0] := 'infantry17';
      [*] = ;         hsfr[1] := gc_ai_unit_musk17;      hsfn[1] := 'musk17';
      [*] = ;         hsfr[2] := gc_ai_unit_uniq_inf17;  hsfn[2] := 'uniq_inf17';
      [*] = ;         hsfr[3] := gc_ai_unit_officer17;   hsfn[3] := 'officer17';
      [*] = ;         hsfr[4] := gc_ai_unit_dragoon17;   hsfn[4] := 'dragoon17';
      [*] = ;         var hsftxt : String = '';
      [*] = ;         var hsfi : Integer;
      [*] = ;         for hsfi := 0 to 4 do
      [*] = ;         begin
      [*] = ;            var hsfid : Integer = -1;
      [*] = ;            var hsfj : Integer;
      [*] = ;            for hsfj := 0 to gc_country_maxmembers-1 do
      [*] = ;            if (hsfid < 0) and (gObjProp[hscid][hsfj].airole = hsfr[hsfi]) then
      [*] = ;            hsfid := hsfj;
      [*] = ;            if (hsfid >= 0) then
      [*] = ;            begin
      [*] = ;               var hsff, hsfw, hsfs, hsfg, hsfir, hsfc : Integer;
      [*] = ;               _unit_GetCostByID(hscid, hsfid, plind, hsff, hsfw, hsfs, hsfg, hsfir, hsfc);
      [*] = ;               hsftxt := hsftxt + hsfn[hsfi] + '=' + gCountry[hscid].members[hsfid];
      [*] = ;               hsftxt := hsftxt + ',hp' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].maxhp);
      [*] = ;               // Attack and defence AS THEY ARE NOW, upgrades included: the engine
      [*] = ;               // keeps them per player in objbase, and an upgrade adds right there
      [*] = ;               // (player.script:1798). A human reads the same numbers off the unit
      [*] = ;               // card in the barracks, so this is not a head start - and without it
      [*] = ;               // the model cannot tell what an upgrade bought her.
      [*] = ;               // Attack is the BEST of the weapon slots, not slot 0. Caught on a live
      [*] = ;               // game 16.09: the musketeer reported atk0, because his shot sits in
      [*] = ;               // another slot - lib/unit.script sets it at a variable weapInd, and
      [*] = ;               // slots 0..2 are all in use across the roster. A human reads one
      [*] = ;               // attack figure off the unit card, and that figure is this one.
      [*] = ;               var hsfa, hsfwi : Integer;
      [*] = ;               for hsfwi := 0 to gc_obj_MaxWeapon-1 do
      [*] = ;               if (gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwi].damage > hsfa) then
      [*] = ;               hsfa := gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwi].damage;
      [*] = ;               hsftxt := hsftxt + ',atk' + IntToStr(hsfa);
      [*] = ;               hsftxt := hsftxt + ',dpike' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].protection[gc_obj_weapon_kind_pike]);
      [*] = ;               hsftxt := hsftxt + ',dsword' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].protection[gc_obj_weapon_kind_sword]);
      [*] = ;               hsftxt := hsftxt + ',dbullet' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].protection[gc_obj_weapon_kind_bullet]);
      [*] = ;               hsftxt := hsftxt + ',food' + IntToStr(hsff) + ',gold' + IntToStr(hsfg);
      [*] = ;               hsftxt := hsftxt + ',iron' + IntToStr(hsfir) + ',coal' + IntToStr(hsfc) + ' ';
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         // Always write the key, even empty: a missing line and 'none' look the
      [*] = ;         // same from Python, and 14.09 we spent a round guessing which it was.
      [*] = ;         if (hsftxt = '') then
      [*] = ;         hsftxt := 'none-found';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'fighters', hsftxt);
      [*] = ;         // --- wood and stone on the ground, within reach --------------------
      [*] = ;         //
      [*] = ;         // The model wrote this urok itself (14.09): '15 men on stone gave +0, it must
      [*] = ;         // be worked out within 40'. She was right and had no way to check: the human
      [*] = ;         // slot reported the STOCK of stone but never how much was left ON THE MAP.
      [*] = ;         // GATHER looks for a deposit within 40 of the base (block_hcmd), so that is
      [*] = ;         // the circle we count - cells of gResGrid, 4 units each, so 10 cells.
      [*] = ;         //
      [*] = ;         // Capacity, not piles: one wood cell holds 2 gatherers, a stone cell 3
      [*] = ;         // (gc_gameplay_resource_maxattackers_*). Free = capacity minus those already
      [*] = ;         // working there. A human sees the same forest and rocks on his screen.
      [*] = ;         var hswn, hswf, hssn, hssf : Integer;
      [*] = ;         var hsgx, hsgy : Integer;
      [*] = ;         var hsbgx : Integer = floor(hscx + (GetMapWidth div 2)) div gc_resgrid_size;
      [*] = ;         var hsbgy : Integer = floor(hscz + (GetMapHeight div 2)) div gc_resgrid_size;
      [*] = ;         for hsgx := 0 to gc_resgrid_countx-1 do
      [*] = ;         for hsgy := 0 to gc_resgrid_county-1 do
      [*] = ;         begin
      [*] = ;            var hswc : Integer = gResGrid[hsgx,hsgy].fResCount[gc_resource_type_wood];
      [*] = ;            var hssc : Integer = gResGrid[hsgx,hsgy].fResCount[gc_resource_type_stone];
      [*] = ;            if ((hswc+hssc) > 0) then
      [*] = ;            begin
      [*] = ;               var hscd : Integer = Round(Sqrt(Sqr(hsbgx-hsgx)+Sqr(hsbgy-hsgy)));
      [*] = ;               if (hscd <= 10) then
      [*] = ;               begin
      [*] = ;                  hswn := hswn + hswc*gc_gameplay_resource_maxattackers_wood;
      [*] = ;                  hssn := hssn + hssc*gc_gameplay_resource_maxattackers_stone;
      [*] = ;                  hswf := hswf + Max(0, hswc*gc_gameplay_resource_maxattackers_wood
      [*] = ;                       - gResGrid[hsgx,hsgy].fWorkerCount[plind][gc_resource_type_wood]);
      [*] = ;                  hssf := hssf + Max(0, hssc*gc_gameplay_resource_maxattackers_stone
      [*] = ;                       - gResGrid[hsgx,hsgy].fWorkerCount[plind][gc_resource_type_stone]);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wood_slots_near', hswn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wood_slots_free', hswf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'stone_slots_near', hssn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'stone_slots_free', hssf);
      [*] = ;         // --- what can be paid for RIGHT NOW -----------------------------------
      [*] = ;         //
      [*] = ;         // The model used to find this out by spending a tick: order it, get nothing,
      [*] = ;         // guess which resource was short. Now the bridge asks the engine the same
      [*] = ;         // question the interface asks - _unit_CanApplyCostByID - and answers before
      [*] = ;         // the order. A human sees it as a greyed-out button.
      [*] = ;         var hsroles : array [0..8] of Integer;
      [*] = ;         var hsrname : array [0..8] of String;
      [*] = ;         hsroles[0] := gc_ai_unit_center;    hsrname[0] := 'center';
      [*] = ;         hsroles[1] := gc_ai_unit_mill;      hsrname[1] := 'mill';
      [*] = ;         hsroles[2] := gc_ai_unit_smith;     hsrname[2] := 'smith';
      [*] = ;         hsroles[3] := gc_ai_unit_ba17;      hsrname[3] := 'ba17';
      [*] = ;         hsroles[4] := gc_ai_unit_store;     hsrname[4] := 'store';
      [*] = ;         hsroles[5] := gc_ai_unit_house;     hsrname[5] := 'house';
      [*] = ;         hsroles[6] := gc_ai_unit_minegold;  hsrname[6] := 'minegold';
      [*] = ;         hsroles[7] := gc_ai_unit_mineiron;  hsrname[7] := 'mineiron';
      [*] = ;         hsroles[8] := gc_ai_unit_minecoal;  hsrname[8] := 'minecoal';
      [*] = ;         var hscan : String = '';
      [*] = ;         var hscant : String = '';
      [*] = ;         var hsri : Integer;
      [*] = ;         for hsri := 0 to 8 do
      [*] = ;         begin
      [*] = ;            var hsrid : Integer = -1;
      [*] = ;            var hsrj : Integer;
      [*] = ;            for hsrj := 0 to gc_country_maxmembers-1 do
      [*] = ;            if (hsrid < 0) and (gObjProp[hscid][hsrj].airole = hsroles[hsri]) then
      [*] = ;            hsrid := hsrj;
      [*] = ;            if (hsrid >= 0) then
      [*] = ;            begin
      [*] = ;               if (_unit_CanApplyCostByID(hscid, hsrid, plind)) then
      [*] = ;               hscan := hscan + hsrname[hsri] + ' '
      [*] = ;               else
      [*] = ;               hscant := hscant + hsrname[hsri] + ' ';
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         // Units too: the peasant and the 17th-century infantry are the two the bot
      [*] = ;         // actually hires. For them the 500-food stop matters as much as the price.
      [*] = ;         if (hspeaid >= 0) then
      [*] = ;         begin
      [*] = ;            if (_unit_CanApplyCostByID(hscid, hspeaid, plind)) then
      [*] = ;            hscan := hscan + 'peasant '
      [*] = ;            else
      [*] = ;            hscant := hscant + 'peasant ';
      [*] = ;         end;
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'can_now', hscan);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'cant_now', hscant);
      [*] = ;         // --- ore deposits: what a player sees on the map ---------------------
      [*] = ;         // The model asked for this itself (questions10, 1:46): 'is there an iron
      [*] = ;         // deposit within 26 of my town centre, and on which side?'. Until now the
      [*] = ;         // human slot reported only how many mines were BUILT, never where the
      [*] = ;         // deposits are - so BUILD minegold was a blind guess, and the bridge could
      [*] = ;         // only answer NO PLACE afterwards.
      [*] = ;         //
      [*] = ;         // _ai_FillOreList (ai.script:220) does not depend on the AI at all: it walks
      [*] = ;         // the environment player's objects and keeps gc_baseid_res of gold, iron and
      [*] = ;         // coal. It is called for bai only (miscext2.script:4419), so on the human
      [*] = ;         // slot the list stays empty - we fill it ourselves, ONCE: deposits do not
      [*] = ;         // appear or move. It also keeps only VISIBLE ones, which is exactly fair:
      [*] = ;         // under fog the model learns no more than the human has scouted.
      [*] = ;         if (gPlayer[plind].aidata.orelist.GetCount = 0) then
      [*] = ;         _ai_FillOreList(plind);
      [*] = ;         var hsod : array [0..2] of Integer;      // distance to nearest FREE deposit
      [*] = ;         var hson : array [0..2] of Integer;      // how many free within reach (26)
      [*] = ;         var hsdx : array [0..2] of Float;
      [*] = ;         var hsdz : array [0..2] of Float;
      [*] = ;         var hsoi : Integer;
      [*] = ;         for hsoi := 0 to 2 do
      [*] = ;         hsod[hsoi] := -1;
      [*] = ;         for hsoi := 0 to gPlayer[plind].aidata.orelist.GetCount-1 do
      [*] = ;         begin
      [*] = ;            var hsoh : Integer = gPlayer[plind].aidata.orelist.Get(hsoi);
      [*] = ;            var hsopr : Pointer = _res_GetTRes(hsoh);
      [*] = ;            if (hsopr<>nil) then
      [*] = ;            begin
      [*] = ;               var hsok : Integer = -1;
      [*] = ;               if (TRes(hsopr).itype = gc_resource_type_gold) then hsok := 0;
      [*] = ;               if (TRes(hsopr).itype = gc_resource_type_iron) then hsok := 1;
      [*] = ;               if (TRes(hsopr).itype = gc_resource_type_coal) then hsok := 2;
      [*] = ;               if (hsok >= 0) then
      [*] = ;               begin
      [*] = ;                  var hsox : Float = GetGameObjectPositionXByHandle(hsoh);
      [*] = ;                  var hsoz : Float = GetGameObjectPositionZByHandle(hsoh);
      [*] = ;                  // Taken? A building standing ON the deposit means a mine is there.
      [*] = ;                  // Same test the game itself uses in _ai_GetClosestOrePlaceWithRes.
      [*] = ;                  gIntegerList.Clear;
      [*] = ;                  _misc_MakeListObjectsInRadius(hsox, hsoz, 1, False,
      [*] = ;                       (1 shl gc_obj_material_building), 1, False, gIntegerList);
      [*] = ;                  var hsfree : Boolean = True;
      [*] = ;                  var hsoj : Integer;
      [*] = ;                  for hsoj := 0 to gIntegerList.GetCount-1 do
      [*] = ;                  begin
      [*] = ;                     var hsbh : Integer = gIntegerList.Get(hsoj);
      [*] = ;                     if (VectorDistance(hsox, 0, hsoz, GetGameObjectPositionXByHandle(hsbh),
      [*] = ;                          0, GetGameObjectPositionZByHandle(hsbh)) < gc_epsilon+0.5) then
      [*] = ;                     hsfree := False;
      [*] = ;                  end;
      [*] = ;                  if (hsfree) then
      [*] = ;                  begin
      [*] = ;                     var hsdist : Integer = Round(VectorDistance(hsox, 0, hsoz, hscx, 0, hscz));
      [*] = ;                     // Within the range the GAME counts as ours: 85,
      [*] = ;                     // gc_ai_dist_mines_expansion (dmscript.global:506). It used to be
      [*] = ;                     // 26 - the radius of the ring search - but since 13.09 a mine is
      [*] = ;                     // placed straight ON the deposit, so that limit no longer applies
      [*] = ;                     // to mines and the state was telling the model a lie.
      [*] = ;                     if (hsdist <= gc_ai_dist_mines_expansion) then
      [*] = ;                     hson[hsok] := hson[hsok] + 1;
      [*] = ;                     if (hsod[hsok] < 0) or (hsdist < hsod[hsok]) then
      [*] = ;                     begin
      [*] = ;                        hsod[hsok] := hsdist;
      [*] = ;                        hsdx[hsok] := hsox - hscx;
      [*] = ;                        hsdz[hsok] := hsoz - hscz;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         // Side as a word: a human reads the minimap, not coordinates. North is -Z.
      [*] = ;         var hsname : array [0..2] of String;
      [*] = ;         hsname[0] := 'gold';
      [*] = ;         hsname[1] := 'iron';
      [*] = ;         hsname[2] := 'coal';
      [*] = ;         for hsoi := 0 to 2 do
      [*] = ;         begin
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ore_' + hsname[hsoi] + '_dist', hsod[hsoi]);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ore_' + hsname[hsoi] + '_near', hson[hsoi]);
      [*] = ;            var hsside : String = '';
      [*] = ;            if (hsod[hsoi] >= 0) then
      [*] = ;            begin
      [*] = ;               if (hsdz[hsoi] < -0.5*Abs(hsdx[hsoi])) then hsside := 'N';
      [*] = ;               if (hsdz[hsoi] >  0.5*Abs(hsdx[hsoi])) then hsside := 'S';
      [*] = ;               if (hsdx[hsoi] >  0.5*Abs(hsdz[hsoi])) then hsside := hsside + 'E';
      [*] = ;               if (hsdx[hsoi] < -0.5*Abs(hsdz[hsoi])) then hsside := hsside + 'W';
      [*] = ;            end;
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'ore_' + hsname[hsoi] + '_side', hsside);
      [*] = ;         end;
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
      [*] = ;            var hsepea, hsebld, hsemil, hsemin, hsj : Integer;
      [*] = ;            var hsxinf, hsxsh, hsxcav : Integer;
      [*] = ;            var hsxmg, hsxmi, hsxmc : Integer;
      [*] = ;            var hsxcen, hsxmill, hsxsm, hsxba, hsxba18 : Integer;
      [*] = ;            var hsxstab, hsxstor, hsxho, hsxtow, hsxmar, hsxaca : Integer;
      [*] = ;            for hsj := 0 to hsec-1 do
      [*] = ;            begin
      [*] = ;               var hseg : Integer = GetGameObjectHandleByIndex(hsj, hseph);
      [*] = ;               var hsep : Pointer = _unit_GetTObj(hseg);
      [*] = ;               if (hsep<>nil) then
      [*] = ;               begin
      [*] = ;                  var hseu : Integer = gObjProp[TObj(hsep).cid][TObj(hsep).id].usage;
      [*] = ;                  if (hseu = gc_obj_usage_peasant) then
      [*] = ;                  hsepea := hsepea + 1;
      [*] = ;                  // Army of the enemy, counted by the SAME usage marks as our own
      [*] = ;                  // (mil_inf/mil_shooters/mil_cav above). The player said 16.09 he
      [*] = ;                  // sees the enemy base, army, peasants and mines on an open map,
      [*] = ;                  // so this is not a head start - it is what the human already has.
      [*] = ;                  if (hseu = gc_obj_usage_lightinfantry) or (hseu = gc_obj_usage_weak) or
      [*] = ;                     (hseu = gc_obj_usage_grenadier) or (hseu = gc_obj_usage_shooter) or
      [*] = ;                     (hseu = gc_obj_usage_archer) or (hseu = gc_obj_usage_fasthorse) or
      [*] = ;                     (hseu = gc_obj_usage_hardhorse) or (hseu = gc_obj_usage_horseshooter) then
      [*] = ;                  hsemil := hsemil + 1;
      [*] = ;                  if (hseu = gc_obj_usage_lightinfantry) or (hseu = gc_obj_usage_weak) or
      [*] = ;                     (hseu = gc_obj_usage_grenadier) then
      [*] = ;                  hsxinf := hsxinf + 1;
      [*] = ;                  if (hseu = gc_obj_usage_shooter) or (hseu = gc_obj_usage_archer) then
      [*] = ;                  hsxsh := hsxsh + 1;
      [*] = ;                  if (hseu = gc_obj_usage_fasthorse) or (hseu = gc_obj_usage_hardhorse) or
      [*] = ;                     (hseu = gc_obj_usage_horseshooter) then
      [*] = ;                  hsxcav := hsxcav + 1;
      [*] = ;                  if (gObjProp[TObj(hsep).cid][TObj(hsep).id].bbuilding) then
      [*] = ;                  begin
      [*] = ;                     hsebld := hsebld + 1;
      [*] = ;                     var hsear : Integer = gObjProp[TObj(hsep).cid][TObj(hsep).id].airole;
      [*] = ;                     if (hsear = gc_ai_unit_minegold) or (hsear = gc_ai_unit_mineiron) or
      [*] = ;                        (hsear = gc_ai_unit_minecoal) then
      [*] = ;                     hsemin := hsemin + 1;
      [*] = ;                     if (hsear = gc_ai_unit_minegold) then hsxmg   := hsxmg + 1;
      [*] = ;                     if (hsear = gc_ai_unit_mineiron) then hsxmi   := hsxmi + 1;
      [*] = ;                     if (hsear = gc_ai_unit_minecoal) then hsxmc   := hsxmc + 1;
      [*] = ;                     if (hsear = gc_ai_unit_center)   then hsxcen  := hsxcen + 1;
      [*] = ;                     if (hsear = gc_ai_unit_mill)     then hsxmill := hsxmill + 1;
      [*] = ;                     if (hsear = gc_ai_unit_smith)    then hsxsm   := hsxsm + 1;
      [*] = ;                     if (hsear = gc_ai_unit_ba17)     then hsxba   := hsxba + 1;
      [*] = ;                     if (hsear = gc_ai_unit_ba18)     then hsxba18 := hsxba18 + 1;
      [*] = ;                     if (hsear = gc_ai_unit_stable)   then hsxstab := hsxstab + 1;
      [*] = ;                     if (hsear = gc_ai_unit_store)    then hsxstor := hsxstor + 1;
      [*] = ;                     if (hsear = gc_ai_unit_house)    then hsxho   := hsxho + 1;
      [*] = ;                     if (hsear = gc_ai_unit_tower)    then hsxtow  := hsxtow + 1;
      [*] = ;                     if (hsear = gc_ai_unit_market)   then hsxmar  := hsxmar + 1;
      [*] = ;                     if (hsear = gc_ai_unit_academi)  then hsxaca  := hsxaca + 1;
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
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_army',     hsemil);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mines',    hsemin);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_inf',      hsxinf);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_shoot',    hsxsh);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_cav',      hsxcav);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mgold',    hsxmg);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_miron',    hsxmi);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mcoal',    hsxmc);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_center',   hsxcen);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mill',     hsxmill);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_smith',    hsxsm);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_ba17',     hsxba);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_ba18',     hsxba18);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_stable',   hsxstab);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_store',    hsxstor);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_house',    hsxho);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_tower',    hsxtow);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_market',   hsxmar);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_academi',  hsxaca);
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
      [*] = ;         // Which upgrades are ALREADY TAKEN and which are being paid for right now.
      [*] = ;         // The engine keeps both in gPlayer[pl].upgstate[cid][i] - the same pair the
      [*] = ;         // native AI asks about in _ai_IsUpgradeInProgressOrDone
      [*] = ;         // (progresseconomicai.inc:1429). Calling that function from here is not
      [*] = ;         // allowed - it lives in another script state - so we read the fields.
      [*] = ;         // ONLY OUR OWN: the player said 16.09 he does not see the enemy upgrades,
      [*] = ;         // so the bridge must not know them either.
      [*] = ;         var hsupgd, hsupgp : String;
      [*] = ;         var hsui : Integer;
      [*] = ;         for hsui := 0 to gc_country_maxupgradecount-1 do
      [*] = ;         begin
      [*] = ;            var hsus : String = gCountry[hscid].upgrade[hsui].id;
      [*] = ;            if (StrLength(hsus) > 3) then
      [*] = ;            begin
      [*] = ;               var hsun : String = SubStr(hsus, 4, StrLength(hsus)-3);
      [*] = ;               if (StrLength(hsupg) > 0) then
      [*] = ;               hsupg := hsupg + ',';
      [*] = ;               hsupg := hsupg + hsun;
      [*] = ;               if (gPlayer[plind].upgstate[hscid][hsui].done) then
      [*] = ;               begin
      [*] = ;                  if (StrLength(hsupgd) > 0) then
      [*] = ;                  hsupgd := hsupgd + ',';
      [*] = ;                  hsupgd := hsupgd + hsun;
      [*] = ;               end;
      [*] = ;               if (gPlayer[plind].upgstate[hscid][hsui].inprogress) then
      [*] = ;               begin
      [*] = ;                  if (StrLength(hsupgp) > 0) then
      [*] = ;                  hsupgp := hsupgp + ',';
      [*] = ;                  hsupgp := hsupgp + hsun;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'upg_avail', hsupg);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'upg_done', hsupgd);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'upg_doing', hsupgp);
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