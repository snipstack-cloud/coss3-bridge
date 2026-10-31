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
      [*] = ;      // ONE STAMP PER SLOT, and this was a defect until 1.10. The key used to be
      [*] = ;      // plain 'wrote', one for everybody, and the whole parser was cleared on each
      [*] = ;      // write. With a SINGLE human slot that worked. In a match of HUMAN AGAINST
      [*] = ;      // BOT there are two, and whichever ticked first in a game second stamped the
      [*] = ;      // key - the other then failed `hsnow - hslast >= 1.0` and wrote NOTHING.
      [*] = ;      // Live game 1.10: coss3_eco_P1.dat was fresh while P0 stayed at the previous
      [*] = ;      // day's match, and nothing said so out loud. Keyed by plind both slots write
      [*] = ;      // every game second; ParserClear is GONE, because clearing the parser is what
      [*] = ;      // would wipe the other slot's stamp.
      [*] = ;      var hslast : Float = ParserGetFloatValueByKeyByHandle(hshb, 'wrote' + IntToStr(plind));
      [*] = ;      // Once per game second is enough: the model thinks every 15-20 seconds, and
      [*] = ;      // a full object scan every frame would be paid for by the simulation.
      [*] = ;      if (hsnow - hslast >= 1.0) or (hsnow < hslast) then
      [*] = ;      begin
      [*] = ;         ParserSetFloatValueByKeyByHandle(hshb, 'wrote' + IntToStr(plind), hsnow);
      [*] = ;         // STAGE MARKS (29.10 night, mac, after D22/D23): twice the state file froze for 158 s and for good while the loop
      [*] = ;         // and the command block went on - this block entered (the stamp above moved) and never reached its save. Every
      [*] = ;         // division and every grid index below is guarded, so the killer is unknown; the mark says how far we got. The
      [*] = ;         // loop block copies stage/stageat into coss3_hb.dat (hs_stage<plind>/hs_at<plind>), where python reads it.
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 0);
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stageat' + IntToStr(plind), Round(hsnow));
      [*] = ;         var hsp : Integer = ParserSelectByKey('br_hp');
      [*] = ;         if (hsp = 0) then
      [*] = ;         hsp := ParserCreate('br_hp');
      [*] = ;         ParserClearByHandle(hsp);
      [*] = ;         var hscid : Integer = gPlayer[plind].cid;
      [*] = ;         var hsph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;         // Group-roll scalars live HERE, not in the nested begin (17.09 lesson: a number declared in a nested block does not accumulate).
      [*] = ;         var hgw, hgdrop, hgforeign, hgownpl : Integer;
      [*] = ;         var hgkeep : Boolean;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'plind',    plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'gametime', Round(hsnow));
      [*] = ;         // SIZE OF THE MAP, in engine units. THE FIELD WAS ALREADY HERE, but
      [*] = ;         // inside the grid section, and that is the whole point of moving it
      [*] = ;         // (27.09): written next to the clock, NOT next to the grids, because
      [*] = ;         // the grid section is gated by
      [*] = ;         // 'if (hscen > 0)', and the first live check found the field missing
      [*] = ;         // for three minutes simply because the town hall was not up yet. The
      [*] = ;         // size of the map has nothing to do with having a town hall.
      [*] = ;         // Why the field at all: a cell of the minimap is width/16, that is 20
      [*] = ;         // units on a 320 map and 16 on 256, and every threshold measured in
      [*] = ;         // cells meant a different distance than the one written down. With it
      [*] = ;         // every record says for itself which map it was played on; records
      [*] = ;         // WITHOUT it are the old 320 ones, and that is what keeps the archive
      [*] = ;         // comparable instead of broken.
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'map_w', GetMapWidth);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'map_h', GetMapHeight);
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 1);
      [*] = ;         var hspea, hsidle, hsbuildp, hsunfin : Integer;
      [*] = ;         var hsonf, hsonw, hsons, hsonmine : Integer;
      [*] = ;         // Mines split by kind. on_mine was one number for gold, iron and coal
      [*] = ;         // together, and a human sees each mine separately - how many work it and
      [*] = ;         // how many places are left. 15.09: BALANCE gold was issued 3 times in 6
      [*] = ;         // games and nothing observable happened, because nobody could see where
      [*] = ;         // the miners actually were.
      [*] = ;         var hsong, hsoni, hsonc : Integer;
      [*] = ;         var hscapg, hscapi, hscapc : Integer;
      [*] = ;         // Mines that actually HOLD someone. A mine built away from the ore
      [*] = ;         // gives no places at all, and the state showed only the total: 'gold=3
      [*] = ;         // (5 of 5 places busy)' reads as 'all good, build more', while one of
      [*] = ;         // the three is empty stone. Measured 17.09 on 15 games of
      [*] = ;         // parallel_start: three gold mines and five places, that is two mines
      [*] = ;         // out of three giving nothing.
      [*] = ;         var hswg : Integer = 0;
      [*] = ;         var hswi : Integer = 0;
      [*] = ;         var hswc : Integer = 0;
      [*] = ;         var hsinf, hsshoot, hscav, hsgun, hsfree : Integer;
      [*] = ;         var hsheld, hsinsq : Integer;   // block task No2 (29.10): holding outside squads / inside squads
      [*] = ;         var hsbusy, hsfreen : Integer;  // 31.10 (Windows): outside squads, not holding - busy (an order) / idle; with my_held and my_insquad they add up to the army
      [*] = ;         // LIST ITEM 3 (30.10 night): squad centres from the MEMBERS. TSquad.fCurX/fCurZ are filled only by the
      [*] = ;         // economic AI (progresseconomicai.inc), which never runs for the human slot - the smoke copy showed cell 8,8
      [*] = ;         // (the map centre) for a squad standing at home. Sums by TObj.squad (= TSquad.fIndex, lib/squad.script:46).
      [*] = ;         var hssqsx, hssqsz : array [0..15] of Float;
      [*] = ;         var hssqsn : array [0..15] of Integer;
      [*] = ;         var hssqk : Integer;
      [*] = ;         for hssqk := 0 to 15 do
      [*] = ;         begin
      [*] = ;            hssqsx[hssqk] := 0;
      [*] = ;            hssqsz[hssqk] := 0;
      [*] = ;            hssqsn[hssqk] := 0;
      [*] = ;         end;
      [*] = ;         var hsoffn, hsdrumn : Integer;
      [*] = ;         var hscen, hsmill, hssmith, hsba, hsstore, hshouse : Integer;
      [*] = ;         var hsmg, hsmi, hsmc, hstow, hsmark, hsacad : Integer;
      [*] = ;         var hsba18, hsstab : Integer;
      [*] = ;         var hswip : String;
      [*] = ;         var hstq : String;   // training queue: who and how many
      [*] = ;         // Per-BUILDING queue. train_now above is the whole player in one
      [*] = ;         // line, and that hid the defect of 17.09: the second barracks stood
      [*] = ;         // empty for 2500 gold because the ALREADY ORDERED guard skipped the
      [*] = ;         // infinite order as soon as the FIRST one had it. Neither the model
      [*] = ;         // nor we could see it - the state said only 'ba17 = 2'.
      [*] = ;         var hsbq : String;   // barracks queues: 1:pikeman:inf,2:none
      [*] = ;         var hsbn : Integer;  // barracks counter for the line above
      [*] = ;         var hsqn : Integer;  // stable counter: the stable has a queue too
      [*] = ;         // NB: 'hssn' is taken - stone_slots_near uses it below (line ~622),
      [*] = ;         // and a repeat in the same begin..end kills the whole Progress tick.
      [*] = ;         var hscx, hscz : Float;
      [*] = ;         var hspeaid : Integer = -1;
      [*] = ;         var hsk : Integer;
      [*] = ;         var hscount : Integer = GetPlayerGameObjectsCountByHandle(hsph);
      [*] = ;         var hsdead : Integer = 0;   // 31.10: dead objects of ours still in the list - counted apart, excluded from everything below
      [*] = ;         for hsk := 0 to hscount-1 do
      [*] = ;         begin
      [*] = ;            var hsgo : Integer = GetGameObjectHandleByIndex(hsk, hsph);
      [*] = ;            var hspo : Pointer = _unit_GetTObj(hsgo);
      [*] = ;            if (hspo<>nil) then
      [*] = ;            if (TObj(hspo).bdead) then
      [*] = ;            hsdead := hsdead + 1;
      [*] = ;            if (hspo<>nil) then
      [*] = ;            // CORPSES STAY IN THE PLAYER'S OBJECT LIST (31.10, 76 'roll cleaned' lines, 16 with >= 50% dead a second after the pick): dead men are not ours to count or to order. Own objects pass.
      [*] = ;            if (not TObj(hspo).bdead) then
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
      [*] = ;                     // WHAT THIS BUILDING IS MAKING RIGHT NOW. Until 17.09 the
      [*] = ;                     // bridge reported the ORDER ('TRAIN pikeman x-1 in 1
      [*] = ;                     // buildings') and never what came of it: no acceptance, no
      [*] = ;                     // queue, no count. Series base14: of 348 TRAIN orders 345
      [*] = ;                     // were infinite, so the model could not tell a running
      [*] = ;                     // conveyor from a stalled one. The queue lives in the
      [*] = ;                     // building's own orders (unit.script:10386-10406): type
      [*] = ;                     // produce, info.produceid is the unit, info.amount is the
      [*] = ;                     // count or the infinite mark.
      [*] = ;                     var hstk : Integer;
      [*] = ;                     for hstk := 0 to gc_obj_MaxOrderCount-1 do
      [*] = ;                     begin
      [*] = ;                        var hstp : Pointer = TObj(hspo).orders[hstk];
      [*] = ;                        if (hstp<>nil) then
      [*] = ;                        if (TOrder(hstp).itype = gc_obj_order_type_produce) then
      [*] = ;                        begin
      [*] = ;                           var hstid : Integer = TOrder(hstp).info.produceid;
      [*] = ;                           var hstam : Integer = TOrder(hstp).info.amount;
      [*] = ;                           if (hstq <> '') then hstq := hstq + ',';
      [*] = ;                           hstq := hstq + gCountry[hscid].members[hstid] + ':';
      [*] = ;                           if (hstam = gc_obj_order_produce_infinite) then
      [*] = ;                           hstq := hstq + 'inf'
      [*] = ;                           else
      [*] = ;                           hstq := hstq + IntToStr(hstam);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     // STABLE 19.09: its queue was collected nowhere, so an idle
      [*] = ;                     // stable was invisible - not busy, not empty. Live game the
      [*] = ;                     // same day: the stable was finished at 15:27 and not a single
      [*] = ;                     // dragoon was ordered until the horizon, while the whole
      [*] = ;                     // 'an idle building makes nobody' logic reads this very line.
      [*] = ;                     // Numbered 's1', 's2' so the reader tells it from a barracks.
      [*] = ;                     if (hsrole = gc_ai_unit_stable) then
      [*] = ;                     begin
      [*] = ;                        hsqn := hsqn + 1;
      [*] = ;                        var hsswhat : String = 'none';
      [*] = ;                        var hssk : Integer;
      [*] = ;                        for hssk := 0 to gc_obj_MaxOrderCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hssp : Pointer = TObj(hspo).orders[hssk];
      [*] = ;                           if (hssp<>nil) then
      [*] = ;                           if (TOrder(hssp).itype = gc_obj_order_type_produce) then
      [*] = ;                           begin
      [*] = ;                              hsswhat := gCountry[hscid].members[TOrder(hssp).info.produceid];
      [*] = ;                              if (TOrder(hssp).info.amount = gc_obj_order_produce_infinite) then
      [*] = ;                              hsswhat := hsswhat + ':inf'
      [*] = ;                              else
      [*] = ;                              hsswhat := hsswhat + ':' + IntToStr(TOrder(hssp).info.amount);
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hsbq <> '') then hsbq := hsbq + ',';
      [*] = ;                        hsbq := hsbq + 's' + IntToStr(hsqn) + ':' + hsswhat;
      [*] = ;                     end;
      [*] = ;                     if (hsrole = gc_ai_unit_ba17) then
      [*] = ;                     begin
      [*] = ;                        hsbn := hsbn + 1;
      [*] = ;                        var hsbwhat : String = 'none';
      [*] = ;                        var hsbk : Integer;
      [*] = ;                        for hsbk := 0 to gc_obj_MaxOrderCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hsbp : Pointer = TObj(hspo).orders[hsbk];
      [*] = ;                           if (hsbp<>nil) then
      [*] = ;                           if (TOrder(hsbp).itype = gc_obj_order_type_produce) then
      [*] = ;                           begin
      [*] = ;                              hsbwhat := gCountry[hscid].members[TOrder(hsbp).info.produceid];
      [*] = ;                              if (TOrder(hsbp).info.amount = gc_obj_order_produce_infinite) then
      [*] = ;                              hsbwhat := hsbwhat + ':inf'
      [*] = ;                              else
      [*] = ;                              hsbwhat := hsbwhat + ':' + IntToStr(TOrder(hsbp).info.amount);
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hsbq <> '') then hsbq := hsbq + ',';
      [*] = ;                        hsbq := hsbq + IntToStr(hsbn) + ':' + hsbwhat;
      [*] = ;                     end;
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
      [*] = ;                     if (hsrole = gc_ai_unit_minegold) and (hscap > 0) then hswg := hswg + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_mineiron) and (hscap > 0) then hswi := hswi + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_minecoal) and (hscap > 0) then hswc := hswc + 1;
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
      [*] = ;                     if (hsusage = gc_obj_usage_cannon) or (hsusage = gc_obj_usage_mcannon) or
      [*] = ;                        (hsusage = gc_obj_usage_mortar) or (hsusage = gc_obj_usage_supermortar) then
      [*] = ;                     hsgun := hsgun + 1;
      [*] = ;                     // Officer and drummer are counted APART: a formation with a
      [*] = ;                     // bonus needs BOTH (_ai_CreateOfficerSquad demands offHnd<>0
      [*] = ;                     // and drumHnd<>0), and the 'NB' formations carry zeroes.
      [*] = ;                     if (hsrole = gc_ai_unit_officer17) then
      [*] = ;                     hsoffn := hsoffn + 1;
      [*] = ;                     if (hsrole = gc_ai_unit_drummer17) then
      [*] = ;                     hsdrumn := hsdrumn + 1;
      [*] = ;                     // FREE MEANS AVAILABLE, AND A MAN HOLDING HIS GROUND IS NOT (5.10, par.102).
      [*] = ;                     // He has no order - he stands - so until now he counted as free, and ATTACK
      [*] = ;                     // count=all would have dissolved the very formation that was told to hold.
      [*] = ;                     // bstandground is the engine's own flag, cleared by any movement order
      [*] = ;                     // (writemove.inc:120), so this needs no bookkeeping of ours.
      [*] = ;                     if (hsusage <> gc_obj_usage_none) and (TObj(hspo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                     if (not TObj(hspo).bstandground) then
      [*] = ;                     hsfree := hsfree + 1;
      [*] = ;                     // WHO ELSE IS HOME (29.10, mac, block task No2, after D20 and exit_all_vs_ai). my_freewar names
      [*] = ;                     // the men a COUNTED order takes: idle and not holding. In D20 python saw 171 at home and asked
      [*] = ;                     // for 171; the counted order took 39, because 143 stood in a LINE120 squad and 33 held ground
      [*] = ;                     // in the FACE screen - and nothing in the state said so. ATTACK all now takes both kinds, but
      [*] = ;                     // the forecast, the critic and the model still could not tell free from held from squad.
      [*] = ;                     // Two more numbers from the same pass, the same tests the command block applies:
      [*] = ;                     // my_insquad - soldiers that belong to a squad (TObj.squad >= 0; ATTACK all drives them as
      [*] = ;                     // squads), my_held - soldiers outside squads standing their ground (bstandground, the flag a
      [*] = ;                     // counted order refuses). Orders are not looked at: a squad on the march is still a squad.
      [*] = ;                     if (hsusage <> gc_obj_usage_none) then
      [*] = ;                     begin
      [*] = ;                        if (TObj(hspo).squad >= 0) then
      [*] = ;                        begin
      [*] = ;                           hsinsq := hsinsq + 1;
      [*] = ;                           var hssqix : Integer = TObj(hspo).squad;
      [*] = ;                           if (hssqix <= 15) then
      [*] = ;                           begin
      [*] = ;                              hssqsx[hssqix] := hssqsx[hssqix] + GetGameObjectPositionXByHandle(hsgo);
      [*] = ;                              hssqsz[hssqix] := hssqsz[hssqix] + GetGameObjectPositionZByHandle(hsgo);
      [*] = ;                              hssqsn[hssqix] := hssqsn[hssqix] + 1;
      [*] = ;                           end;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        if (TObj(hspo).bstandground) then
      [*] = ;                        begin
      [*] = ;                           hsheld := hsheld + 1;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        if (TObj(hspo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                        begin
      [*] = ;                           hsfreen := hsfreen + 1;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           hsbusy := hsbusy + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         // --- WHAT BECAME OF THE WAVE -----------------------------------
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 2);
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
      [*] = ;         // 'IN THE FIELD' BY CELL, not by 60 units (5.10, par.99). The same measure
      [*] = ;         // sits in block_hcmd (hafn/hafr): what we report here as away must be exactly
      [*] = ;         // what the command block can order, or a heap of 74 ends up away for neither -
      [*] = ;         // too close for RETREAT and ENGAGE, under an order so not free for ATTACK.
      [*] = ;         // cHmGrid and hmw are declared FURTHER DOWN, with the minimap, and a name used
      [*] = ;         // before its declaration kills the whole tick - hence the copies here, with the
      [*] = ;         // same values and this note. hscx/hscz are final: this is the second pass.
      [*] = ;         const cHmHome = 1;         // home = the hall cell and the eight around it
      [*] = ;         var hqn  : Integer = 16;   // cHmGrid below; the grids must match
      [*] = ;         var hqw  : Integer = GetMapWidth;
      [*] = ;         var hqh  : Integer = GetMapHeight;
      [*] = ;         var hqhw : Integer = hqw div 2;
      [*] = ;         var hqhh : Integer = hqh div 2;
      [*] = ;         var hqbx : Integer = floor((hscx+hqhw)*hqn/hqw);
      [*] = ;         var hqby : Integer = floor((hscz+hqhh)*hqn/hqh);
      [*] = ;         var hswaway : Integer = 0;   // soldiers in the field: further than cHmHome cells
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
      [*] = ;                     var hqux : Integer = floor((GetGameObjectPositionXByHandle(hswh)+hqhw)*hqn/hqw);
      [*] = ;                     var hquy : Integer = floor((GetGameObjectPositionZByHandle(hswh)+hqhh)*hqn/hqh);
      [*] = ;                     var hqdc : Integer = Round(Abs(hqux - hqbx));
      [*] = ;                     var hqdy : Integer = Round(Abs(hquy - hqby));
      [*] = ;                     // Chebyshev distance without a Max: the larger of the two.
      [*] = ;                     if (hqdc < hqdy) then hqdc := hqdy;
      [*] = ;                     // mil_near and mil_far stay in UNITS on purpose: they answer 'how far', and
      [*] = ;                     // only the yes/no of 'in the field' moved to cells.
      [*] = ;                     if (hqdc > cHmHome) then
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_dead',   hsdead);
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'work_gold', hswg);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'work_iron', hswi);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'work_coal', hswc);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'cap_iron',  hscapi);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'cap_coal',  hscapc);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'on_build',  hsbuildp);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'idle_pea',  hsidle);
      [*] = ;         // BLOCK TARGETS AND THE SINK SURPLUS (29.10 evening, mac, after balance_sink_vs_ai). The sink seats every idle
      [*] = ;         // man, so python saw 'idle 0' for the whole game and its own transfer rule (par. 170p) refused every fill for
      [*] = ;         // want of donors: stone 3 -> 5 waited from 2:02 to 2:50, the gold mine from 3:27 to 4:07. What python needs
      [*] = ;         // is the number of men the block parked ABOVE its targets - they are as free as idle men. The targets live
      [*] = ;         // in br_hbal (written by the command block, see TOPUP STORE); absent = python never asked, every man there
      [*] = ;         // is parked. tgt_* say the targets themselves, sink_pea the sum of the surpluses.
      [*] = ;         var hstgp : Integer = ParserSelectByKey('br_hbal');
      [*] = ;         var hstgf : Integer = -1;
      [*] = ;         var hstgw : Integer = -1;
      [*] = ;         var hstgs : Integer = -1;
      [*] = ;         if (hstgp <> 0) then
      [*] = ;         begin
      [*] = ;            if (ParserGetValueByKeyByHandle(hstgp, 'tf' + IntToStr(plind)) <> '') then
      [*] = ;            begin
      [*] = ;               hstgf := ParserGetIntValueByKeyByHandle(hstgp, 'tf' + IntToStr(plind));
      [*] = ;            end;
      [*] = ;            if (ParserGetValueByKeyByHandle(hstgp, 'tw' + IntToStr(plind)) <> '') then
      [*] = ;            begin
      [*] = ;               hstgw := ParserGetIntValueByKeyByHandle(hstgp, 'tw' + IntToStr(plind));
      [*] = ;            end;
      [*] = ;            if (ParserGetValueByKeyByHandle(hstgp, 'ts' + IntToStr(plind)) <> '') then
      [*] = ;            begin
      [*] = ;               hstgs := ParserGetIntValueByKeyByHandle(hstgp, 'ts' + IntToStr(plind));
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         var hssink : Integer = 0;
      [*] = ;         if (hstgf < 0) then hssink := hssink + hsonf;
      [*] = ;         if (hstgf >= 0) then
      [*] = ;         begin
      [*] = ;            if (hsonf > hstgf) then hssink := hssink + hsonf - hstgf;
      [*] = ;         end;
      [*] = ;         if (hstgw < 0) then hssink := hssink + hsonw;
      [*] = ;         if (hstgw >= 0) then
      [*] = ;         begin
      [*] = ;            if (hsonw > hstgw) then hssink := hssink + hsonw - hstgw;
      [*] = ;         end;
      [*] = ;         if (hstgs < 0) then hssink := hssink + hsons;
      [*] = ;         if (hstgs >= 0) then
      [*] = ;         begin
      [*] = ;            if (hsons > hstgs) then hssink := hssink + hsons - hstgs;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'tgt_food',  hstgf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'tgt_wood',  hstgw);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'tgt_stone', hstgs);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'sink_pea',  hssink);
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_guns',     hsgun);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_officers', hsoffn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_drummers', hsdrumn);
      [*] = ;         // Squads and the formation they stand in. The bonus lives in
      [*] = ;         // gFormation and differs on the move and at a halt: LINE15 gives
      [*] = ;         // +2/+2 walking and +7/+7 standing (formations.cfg). Without this
      [*] = ;         // the model cannot tell whether the formation it built is worth
      [*] = ;         // anything at all.
      [*] = ;         var hssq : Integer = gPlayer[plind].squads.GetCount;
      [*] = ;         var hssqu, hssqi : Integer;
      [*] = ;         var hssqf : Integer = -1;
      [*] = ;         var hssqh : Integer = 0;   // block task No3 (29.10): does the largest squad hunt (fSearchVictim)
      [*] = ;         var hssqg : Integer = 0;   // ... and does it stand its ground (fStandGround)
      [*] = ;         // BLOCK LIST ITEM 3 (30.10 night): EVERY squad, not only the largest - 'uid,men,formation,cx,cy,hold,hunt,holdmode'
      [*] = ;         // per squad, ';' between, 'none' when there is none; cell = minimap cell (width/16) of the squad centre.
      [*] = ;         var hssql : String = '';
      [*] = ;         var hssqln : Integer = 0;
      [*] = ;         var hssqmw : Integer = GetMapWidth;
      [*] = ;         var hssqmh : Integer = GetMapHeight;
      [*] = ;         for hssqi := 0 to hssq-1 do
      [*] = ;         begin
      [*] = ;            var hspsq : Pointer = gPlayer[plind].squads.Get(hssqi);
      [*] = ;            if (hspsq<>nil) then
      [*] = ;            if (TSquad(hspsq).GetCount > hssqu) then
      [*] = ;            begin
      [*] = ;               hssqu := TSquad(hspsq).GetCount;
      [*] = ;               hssqf := TSquad(hspsq).fFormation;
      [*] = ;               hssqh := 0;
      [*] = ;               if (TSquad(hspsq).fSearchVictim) then hssqh := 1;
      [*] = ;               hssqg := 0;
      [*] = ;               if (TSquad(hspsq).fStandGround) then hssqg := 1;
      [*] = ;            end;
      [*] = ;            if (hspsq<>nil) then
      [*] = ;            if (hssqln < 16) then
      [*] = ;            begin
      [*] = ;               var hssqfi : Integer = TSquad(hspsq).fIndex;
      [*] = ;               var hssqpx : Float = TSquad(hspsq).fCurX;
      [*] = ;               var hssqpz : Float = TSquad(hspsq).fCurZ;
      [*] = ;               if (hssqfi >= 0) and (hssqfi <= 15) then
      [*] = ;               if (hssqsn[hssqfi] > 0) then
      [*] = ;               begin
      [*] = ;                  hssqpx := hssqsx[hssqfi] / hssqsn[hssqfi];
      [*] = ;                  hssqpz := hssqsz[hssqfi] / hssqsn[hssqfi];
      [*] = ;               end;
      [*] = ;               var hssqcx : Integer = floor((hssqpx + (hssqmw div 2)) * 16 / hssqmw);
      [*] = ;               var hssqcy : Integer = floor((hssqpz + (hssqmh div 2)) * 16 / hssqmh);
      [*] = ;               var hssqfs : String = '-';
      [*] = ;               if (TSquad(hspsq).fFormation >= 0) then hssqfs := gFormation[TSquad(hspsq).fFormation].sid;
      [*] = ;               var hssqg2 : Integer = 0;
      [*] = ;               if (TSquad(hspsq).fStandGround) then hssqg2 := 1;
      [*] = ;               var hssqh2 : Integer = 0;
      [*] = ;               if (TSquad(hspsq).fSearchVictim) then hssqh2 := 1;
      [*] = ;               var hssqm2 : Integer = 0;
      [*] = ;               if (TSquad(hspsq).fHoldMode) then hssqm2 := 1;
      [*] = ;               if (hssqln > 0) then
      [*] = ;               hssql := hssql + ';';
      [*] = ;               hssql := hssql + IntToStr(TSquad(hspsq).fUID) + ',' + IntToStr(TSquad(hspsq).GetCount) + ',' + hssqfs + ',' +
      [*] = ;                    IntToStr(hssqcx) + ',' + IntToStr(hssqcy) + ',' + IntToStr(hssqg2) + ',' + IntToStr(hssqh2) + ',' + IntToStr(hssqm2);
      [*] = ;               hssqln := hssqln + 1;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'squads',      hssq);
      [*] = ;         if (hssql = '') then
      [*] = ;         hssql := 'none';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'squads_list', hssql);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'squads_list_n', hssqln);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'squad_units', hssqu);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'squad_hunt',  hssqh);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'squad_hold',  hssqg);
      [*] = ;         if (hssqf >= 0) then
      [*] = ;         begin
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'squad_form', gFormation[hssqf].sid);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'squad_dmg',  gFormation[hssqf].bonusdamage);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'squad_def',  gFormation[hssqf].bonusshield);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'squad_hdmg', gFormation[hssqf].bonusdamagehold);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'squad_hdef', gFormation[hssqf].bonusshieldhold);
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_shooters', hsshoot);
      [*] = ;         // OUR OWN losses from the same engine statistics: peasants and fighters of
      [*] = ;         // ours that died since the game began. Until now the trace could only
      [*] = ;         // guess losses from army deltas, and hiring hid them.
      [*] = ;         var hslp, hslm, hslk : Integer;
      [*] = ;         for hslk := 0 to gc_country_maxmembers-1 do
      [*] = ;         begin
      [*] = ;            var hslu : Integer = gObjProp[hscid][hslk].usage;
      [*] = ;            if (hslu = gc_obj_usage_peasant) then
      [*] = ;            hslp := hslp + gPlayer[plind].stat.killed[hscid][hslk];
      [*] = ;            if (hslu = gc_obj_usage_lightinfantry) or (hslu = gc_obj_usage_weak) or (hslu = gc_obj_usage_grenadier) or
      [*] = ;               (hslu = gc_obj_usage_shooter) or (hslu = gc_obj_usage_archer) or (hslu = gc_obj_usage_fasthorse) or
      [*] = ;               (hslu = gc_obj_usage_hardhorse) or (hslu = gc_obj_usage_horseshooter) then
      [*] = ;            hslm := hslm + gPlayer[plind].stat.killed[hscid][hslk];
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_pea_lost', hslp);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_mil_lost', hslm);
      [*] = ;         // KILL EVENTS (27.09). Written by block_kills.inc from the death gate of
      [*] = ;         // _misc_DoDamage into the named parser br_kills: 'seq,gt,vpl,vcls,vx,vy,
      [*] = ;         // kpl,kcls,kx,ky,w' per death, a ring of 128 (48 until 29.09: a live player
      [*] = ;         // gathers a bigger army and fights in one heap, and an incomplete window is
      [*] = ;         // thrown out of every count of 18-22). Handed out here BY KEY over the
      [*] = ;         // whole ring - never by enumeration, that part of the parser is unproven in this
      [*] = ;         // bridge. Cumulative and numbered on purpose: python reads every fifth write,
      [*] = ;         // keeps the last sequence number it saw and takes only what is new; kills_n
      [*] = ;         // says how many there were in all, so a gap wider than the ring is visible and
      [*] = ;         // not silent. Placed NEXT TO THE COUNTER and outside the town-hall gate: men die
      [*] = ;         // whether or not we have a hall, and my_mil_lost is written right above.
      [*] = ;         var hskp : Integer = ParserSelectByKey('br_kills');
      [*] = ;         if (hskp = 0) then
      [*] = ;         hskp := ParserCreate('br_kills');
      [*] = ;         // A new match in the same process: the clock went backwards (the same test
      [*] = ;         // br_hstate makes for its own clock). Without this the deaths of the previous
      [*] = ;         // match would ride into the next one.
      [*] = ;         if (hsnow < hslast) then
      [*] = ;         ParserClearByHandle(hskp);
      [*] = ;         var hskn : Integer = ParserGetIntValueByKeyByHandle(hskp, 'n');
      [*] = ;         var hsks : String = '';
      [*] = ;         var hski : Integer;
      [*] = ;         var hsk0 : Integer = hskn - 127;
      [*] = ;         if (hsk0 < 1) then
      [*] = ;         hsk0 := 1;
      [*] = ;         for hski := hsk0 to hskn do
      [*] = ;         begin
      [*] = ;            var hske : String = ParserGetValueByKeyByHandle(hskp, 'e' + IntToStr(hski mod 128));
      [*] = ;            if (hske <> '') then
      [*] = ;            begin
      [*] = ;               if (hsks <> '') then
      [*] = ;               hsks := hsks + ';';
      [*] = ;               hsks := hsks + hske;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         if (hsks = '') then
      [*] = ;         hsks := 'none';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'kills', hsks);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'kills_n', hskn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'mil_cav',      hscav);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_freewar',   hsfree);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_held',      hsheld);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_insquad',   hsinsq);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_busy',      hsbusy);     // 31.10: alive, outside squads, not holding, with an order (marching/fighting)
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'my_free_nosq', hsfreen);    // 31.10: alive, outside squads, not holding, idle (my_freewar also counts idle squad men)
      [*] = ;         // HOME DEFENCE REFLEX of the command block (30.10): on/off and how many enemy soldiers it saw within 4 cells.
      [*] = ;         var hsdf : Integer = ParserSelectByKey('br_hdef');
      [*] = ;         if (hsdf <> 0) then
      [*] = ;         begin
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'defend_on', ParserGetIntValueByKeyByHandle(hsdf, 'on' + IntToStr(plind)));
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'defend_n', ParserGetIntValueByKeyByHandle(hsdf, 'n' + IntToStr(plind)));
      [*] = ;         end;
      [*] = ;         ParserSetFloatValueByKeyByHandle(hsp, 'my_x', hscx);
      [*] = ;         ParserSetFloatValueByKeyByHandle(hsp, 'my_z', hscz);
      [*] = ;         // --- WHICH FIGHTERS THIS NATION CAN HIRE ----------------------------
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 3);
      [*] = ;         //
      [*] = ;         // A newcomer opens the barracks and reads what is inside: name, price,
      [*] = ;         // health. The bot never had that. Result, 12 games of 14.09: the army was
      [*] = ;         // made of pikemen ONLY (infantry17 ordered 144 times, musk17 zero times),
      [*] = ;         // and every wave died at the enemy base without killing a single peasant.
      [*] = ;         // musketeernet was available all along - she simply could not see it.
      [*] = ;         //
      [*] = ;         // No aiforce here on purpose: that number lives inside the AI and a human
      [*] = ;         // never sees it. Price and health he does see, by clicking the unit.
      [*] = ;         // OFFICER AND DRUMMER ARE NOT LISTED, on purpose. Both are made
      [*] = ;         // in the academy only (country.script:3047,3051 - the requirement
      [*] = ;         // is csid+'aca'), and the academy is forbidden by a HACKATHON
      [*] = ;         // RULE, not by a setting we could change. Listing them would be
      [*] = ;         // the same lie the bridge told three times on 16.09: naming as
      [*] = ;         // available something that can never be had. They were shown here
      [*] = ;         // for two days and the model never ordered them once in 1339
      [*] = ;         // ticks - no harm done, but no reason to keep it either.
      [*] = ;         // OUR types of the 18th century too (29.09, P8). The same five roles as in
      [*] = ;         // the enemy list below, for the same reason: after cen.1 our own numbers
      [*] = ;         // change, and the law must not keep counting a musketeer17. Whether the
      [*] = ;         // MODEL is told about them is decided in python by --c18-numbers: the field
      [*] = ;         // is the block's business, the request is a lever (28.09).
      [*] = ;         var hsfr : array [0..8] of Integer;
      [*] = ;         var hsfn : array [0..8] of String;
      [*] = ;         hsfr[0] := gc_ai_unit_infantry17;  hsfn[0] := 'infantry17';
      [*] = ;         hsfr[1] := gc_ai_unit_musk17;      hsfn[1] := 'musk17';
      [*] = ;         hsfr[2] := gc_ai_unit_uniq_inf17;  hsfn[2] := 'uniq_inf17';
      [*] = ;         hsfr[3] := gc_ai_unit_dragoon17;   hsfn[3] := 'dragoon17';
      [*] = ;         hsfr[4] := gc_ai_unit_pikeman18;   hsfn[4] := 'pikeman18';
      [*] = ;         hsfr[5] := gc_ai_unit_musk18;      hsfn[5] := 'musk18';
      [*] = ;         hsfr[6] := gc_ai_unit_dragun18;    hsfn[6] := 'dragun18';
      [*] = ;         hsfr[7] := gc_ai_unit_uniq_inf18;  hsfn[7] := 'uniq_inf18';
      [*] = ;         hsfr[8] := gc_ai_unit_uniq_cav18;  hsfn[8] := 'uniq_cav18';
      [*] = ;         var hsftxt : String = '';
      [*] = ;         var hsinfid : Integer = -1;   // id of the line infantry, for can_inf
      [*] = ;         var hsfi : Integer;
      [*] = ;         for hsfi := 0 to 8 do
      [*] = ;         begin
      [*] = ;            var hsfid : Integer = -1;
      [*] = ;            var hsfj : Integer;
      [*] = ;            for hsfj := 0 to gc_country_maxmembers-1 do
      [*] = ;            if (hsfid < 0) and (gObjProp[hscid][hsfj].airole = hsfr[hsfi]) then
      [*] = ;            hsfid := hsfj;
      [*] = ;            if (hsfid >= 0) then
      [*] = ;            begin
      [*] = ;               if (hsfi = 0) then
      [*] = ;               hsinfid := hsfid;
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
      [*] = ;               // Index of the BEST slot, not just its damage: weapon kind and reload
      [*] = ;               // pause must come from the SAME slot, or damage is taken from one
      [*] = ;               // weapon and speed from another. Damage = attacker's attack minus the
      [*] = ;               // target's protection FOR THAT WEAPON KIND (lib/miscext2.script:380,
      [*] = ;               // 434), so without kind there is no telling which protection to use.
      [*] = ;               var hsfa, hsfwi, hsfwb : Integer;
      [*] = ;               hsfwb := -1;
      [*] = ;               for hsfwi := 0 to gc_obj_MaxWeapon-1 do
      [*] = ;               if (gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwi].damage > hsfa) then
      [*] = ;               begin
      [*] = ;                  hsfa := gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwi].damage;
      [*] = ;                  hsfwb := hsfwi;
      [*] = ;               end;
      [*] = ;               hsftxt := hsftxt + ',atk' + IntToStr(hsfa);
      [*] = ;               // Pause goes out in HUNDREDTHS: _misc_FramesToTime returns a fraction,
      [*] = ;               // and rounding it to a whole number turned the pikeman's pause into 0
      [*] = ;               // on a live game 19.09 while the musketeer's came out as 4.
      [*] = ;               if (hsfwb >= 0) then
      [*] = ;               begin
      [*] = ;                  hsftxt := hsftxt + ',wkind' + IntToStr(gObjProp[hscid][hsfid].weapon[hsfwb].kind);
      [*] = ;                  hsftxt := hsftxt + ',pause' + IntToStr(Round(gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwb].pause*100));
      [*] = ;                  // RANGE (20.09): radiusmax of the same weapon slot, in
      [*] = ;                  // HUNDREDTHS like pause. Declared in SetObjBaseWeapon
      [*] = ;                  // (unit.script:520) as pixels and stored already divided
      [*] = ;                  // by gc_pixels_to_tile = 53.3333 (dmscript.global:172).
      [*] = ;                  // Pikeman 100 px -> 1.9, musketeer 800 px -> 15.0: an
      [*] = ;                  // EIGHTFOLD gap, and it decides how many free volleys a
      [*] = ;                  // shooter gets while the pikeman closes the distance.
      [*] = ;                  // Without it the bridge scored musketeer against pikeman
      [*] = ;                  // as 562 and flagged its own number as unusable.
      [*] = ;                  hsftxt := hsftxt + ',rmax' + IntToStr(Round(gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwb].radiusmax*100));
      [*] = ;                  // WHERE THE ATTACK NUMBER COMES FROM, decomposed (28.09, request of the mac).
      [*] = ;                  // The engine keeps FOUR numbers per weapon (classes.script:3549): damageinit from
      [*] = ;                  // the data, damagestatic - the flat bonus of blacksmith upgrades, damagepercent -
      [*] = ;                  // the PERCENT bonus of academy upgrades, and damage, which it recomputes on every
      [*] = ;                  // upgrade of either kind as
      [*] = ;                  //     damage := floor((damageinit + damagestatic) * (1 + damagepercent / 100))
      [*] = ;                  // (player.script:1765 for the flat kind, :1784 for the percent kind).
      [*] = ;                  // 'atk' above is that damage, so academy percent is ALREADY in it - counting
      [*] = ;                  // upgrades by the taken-list to add it on top would count it twice. The two terms
      [*] = ;                  // go out anyway, and not for beauty: with them the claim above is CHECKABLE
      [*] = ;                  // (atk must equal the formula), and the simulator can tell a flat bonus from a
      [*] = ;                  // percent one when it decides which upgrade is worth buying. From the SAME weapon
      [*] = ;                  // slot as atk - a number from another slot describes another weapon.
      [*] = ;
      [*] = ;                  hsftxt := hsftxt + ',dmgs' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwb].damagestatic);
      [*] = ;                  hsftxt := hsftxt + ',dmgp' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwb].damagepercent);
      [*] = ;                  hsftxt := hsftxt + ',dinit' + IntToStr(gPlayer[plind].objbase[hscid][hsfid].weapon[hsfwb].damageinit);
      [*] = ;               end;
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
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'train_now', hstq);
      [*] = ;         if (hsbq = '') then
      [*] = ;         hsbq := 'none-built';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'ba_queues', hsbq);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'fighters', hsftxt);
      [*] = ;         // WHY THE HIRING STOPPED, in the engine's own words. Below a food
      [*] = ;         // floor the game halts production SILENTLY, and the bridge kept
      [*] = ;         // reporting 'TRAIN ordered in 1 buildings' as if all was well. The
      [*] = ;         // computer slot has had these three fields since the start
      [*] = ;         // (block_state.inc:33-35) and the prompt already knows how to read
      [*] = ;         // them - the human slot simply never wrote them. Series base12,
      [*] = ;         // 16.09: the ten games that never took the goal spent 14.5 ticks
      [*] = ;         // under the food floor AFTER minute five, the five that took it
      [*] = ;         // spent 1.2, and nothing in the state said why.
      [*] = ;         // bfamine is the engine's own flag: it goes up when the player
      [*] = ;         // could not pay the food upkeep this tick (player.script:304).
      [*] = ;         if (hspeaid >= 0) then
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'can_pea',
      [*] = ;              _unit_CanApplyCountCostByID(hscid, hspeaid, plind, 1));
      [*] = ;         if (hsinfid >= 0) then
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'can_inf',
      [*] = ;              _unit_CanApplyCountCostByID(hscid, hsinfid, plind, 1));
      [*] = ;         ParserSetBoolValueByKeyByHandle(hsp, 'famine', gPlayer[plind].bfamine);
      [*] = ;         // --- wood and stone on the ground, within reach --------------------
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 4);
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
      [*] = ;         // IS THE FIELD RIPE? The model could not know. The bridge said 'wait'
      [*] = ;         // while the field grew and then simply fell silent - and silence is not
      [*] = ;         // a signal. Measured 17.09 on parallel_start: the mill was ready at 29 s,
      [*] = ;         // the field ripe around 134 s, and the first peasant went to food only at
      [*] = ;         // 230 s. A hundred seconds of the win from an early mill were eaten by
      [*] = ;         // the model not noticing the moment.
      [*] = ;         //
      [*] = ;         // Counted EXACTLY as the BALANCE command counts it - same search, same
      [*] = ;         // filter (brised), same radius, around the MILL - so the state and the
      [*] = ;         // command can never disagree.
      [*] = ;         var hsfrd : Integer = 0;
      [*] = ;         var hsmx : Float = hscx;
      [*] = ;         var hsmz : Float = hscz;
      [*] = ;         var hsmfound : Integer = 0;
      [*] = ;         var hsmk : Integer;
      [*] = ;         for hsmk := 0 to hscount-1 do
      [*] = ;         begin
      [*] = ;            var hsmgo : Integer = GetGameObjectHandleByIndex(hsmk, hsph);
      [*] = ;            var hsmpo : Pointer = _unit_GetTObj(hsmgo);
      [*] = ;            if (hsmpo<>nil) and (hsmfound = 0) then
      [*] = ;            if (gObjProp[TObj(hsmpo).cid][TObj(hsmpo).id].airole = gc_ai_unit_mill) then
      [*] = ;            if (TObj(hsmpo).bbuilt) then
      [*] = ;            begin
      [*] = ;               hsmfound := hsmgo;
      [*] = ;               hsmx := GetGameObjectPositionXByHandle(hsmgo);
      [*] = ;               hsmz := GetGameObjectPositionZByHandle(hsmgo);
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         if (hsmfound <> 0) then
      [*] = ;         begin
      [*] = ;            gIntegerList.Clear;
      [*] = ;            _misc_MakeListEnvironmentInRadius(hsmx, hsmz, 40, True, True, False, False, False, gIntegerList);
      [*] = ;            var hsfk : Integer;
      [*] = ;            for hsfk := 0 to gIntegerList.GetCount-1 do
      [*] = ;            begin
      [*] = ;               var hsfp : Pointer = _res_GetTRes(gIntegerList.Get(hsfk));
      [*] = ;               if (hsfp<>nil) then
      [*] = ;               if (TRes(hsfp).brised) and (TRes(hsfp).itype = gc_resource_type_food) then
      [*] = ;               hsfrd := hsfrd + 1;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'food_ready', hsfrd);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wood_slots_near', hswn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'wood_slots_free', hswf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'stone_slots_near', hssn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'stone_slots_free', hssf);
      [*] = ;         // --- what can be paid for RIGHT NOW -----------------------------------
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 5);
      [*] = ;         //
      [*] = ;         // The model used to find this out by spending a tick: order it, get nothing,
      [*] = ;         // guess which resource was short. Now the bridge asks the engine the same
      [*] = ;         // question the interface asks - _unit_CanApplyCostByID - and answers before
      [*] = ;         // the order. A human sees it as a greyed-out button.
      [*] = ;         // STABLE added 18.09: the dragoon is the only unit of ours that catches
      [*] = ;         // a fleeing peasant (the objective), and both the stable and the dragoon
      [*] = ;         // need nothing but the blacksmith (country.script:2929, 2978). The list
      [*] = ;         // had nine roles and no stable, so 'stable' never reached can_now or
      [*] = ;         // cant_now, and the model never built one: zero cavalry in every game.
      [*] = ;         var hsroles : array [0..10] of Integer;
      [*] = ;         var hsrname : array [0..10] of String;
      [*] = ;         hsroles[0] := gc_ai_unit_center;    hsrname[0] := 'center';
      [*] = ;         hsroles[1] := gc_ai_unit_mill;      hsrname[1] := 'mill';
      [*] = ;         hsroles[2] := gc_ai_unit_smith;     hsrname[2] := 'smith';
      [*] = ;         hsroles[3] := gc_ai_unit_ba17;      hsrname[3] := 'ba17';
      [*] = ;         hsroles[4] := gc_ai_unit_store;     hsrname[4] := 'store';
      [*] = ;         hsroles[5] := gc_ai_unit_house;     hsrname[5] := 'house';
      [*] = ;         hsroles[6] := gc_ai_unit_minegold;  hsrname[6] := 'minegold';
      [*] = ;         hsroles[7] := gc_ai_unit_mineiron;  hsrname[7] := 'mineiron';
      [*] = ;         hsroles[8] := gc_ai_unit_minecoal;  hsrname[8] := 'minecoal';
      [*] = ;         hsroles[9] := gc_ai_unit_stable;    hsrname[9] := 'stable';
      [*] = ;         // ACADEMY (20.09) - the same hole the stable had. It was missing
      [*] = ;         // from this list, so it never reached can_now, cant_now or the
      [*] = ;         // price line: a full 20-minute game with two barracks showed it
      [*] = ;         // in NONE of 59 ticks. The model knew what academy upgrades give
      [*] = ;         // (they are listed with prices) and still could not build the
      [*] = ;         // building that unlocks them.
      [*] = ;         hsroles[10] := gc_ai_unit_academi;  hsrname[10] := 'academi';
      [*] = ;         var hscan : String = '';
      [*] = ;         var hscant : String = '';
      [*] = ;         // PRICE of every building, same form as 'fighters'. Without it the
      [*] = ;         // model knew only WHETHER it can pay, never HOW MUCH - and could not
      [*] = ;         // see the one price that decides the early game: every next building
      [*] = ;         // of the same kind costs costpercent=500 per cent of the previous one
      [*] = ;         // (unit.script:2472), so the second barracks is 2500 gold where the
      [*] = ;         // first was 500. The engine already applies it - the cost is asked
      [*] = ;         // for THIS player with his current count, exactly as the build panel
      [*] = ;         // shows it to a human.
      [*] = ;         var hsbtxt : String = '';
      [*] = ;         var hsri : Integer;
      [*] = ;         for hsri := 0 to 10 do
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
      [*] = ;               var hsbf, hsbw, hsbs, hsbg, hsbir, hsbc : Integer;
      [*] = ;               _unit_GetCostByID(hscid, hsrid, plind, hsbf, hsbw, hsbs, hsbg, hsbir, hsbc);
      [*] = ;               hsbtxt := hsbtxt + hsrname[hsri] + '=';
      [*] = ;               hsbtxt := hsbtxt + 'food' + IntToStr(hsbf) + ',wood' + IntToStr(hsbw);
      [*] = ;               hsbtxt := hsbtxt + ',stone' + IntToStr(hsbs) + ',gold' + IntToStr(hsbg);
      [*] = ;               hsbtxt := hsbtxt + ',iron' + IntToStr(hsbir) + ',coal' + IntToStr(hsbc) + ' ';
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
      [*] = ;         // Always write the key, even empty - a missing line and an empty one
      [*] = ;         // look the same from Python.
      [*] = ;         if (hsbtxt = '') then
      [*] = ;         hsbtxt := 'none-found';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'build_cost', hsbtxt);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'can_now', hscan);
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'cant_now', hscant);
      [*] = ;         // --- ore deposits: what a player sees on the map ---------------------
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 6);
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 7);
      [*] = ;         // --- MINIMAP ----------------------------------------------------
      [*] = ;         // A human sees the minimap at all times, and on an open map it shows
      [*] = ;         // everything on it. Until 16.09 the model had distances and compass
      [*] = ;         // words only ('nearest enemy 180', 'gold to the north-east'): where
      [*] = ;         // to walk around, and where the enemy army stands, was unsayable.
      [*] = ;         // The shape is taken from block_state.inc of the computer slot where
      [*] = ;         // it worked; its 'case' is replaced by 'if' - one-line case branches
      [*] = ;         // have brought the tick down in this language before.
      [*] = ;         const cHmGrid = 16;
      [*] = ;         var hmbase : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmforce : array [0..15] of array [0..15] of Integer;
      [*] = ;         // Where his moving soldiers are GOING, per destination cell (24.09).
      [*] = ;         // p<n>_mv_cx/cy below give ONE average target for all of them: two
      [*] = ;         // detachments heading apart average to a point between them, and the
      [*] = ;         // model cannot tell a march on our base from a march past it. Same
      [*] = ;         // marks as frow; python splits it into detachments and directions.
      [*] = ;         var hmdest : array [0..15] of array [0..15] of Integer;
      [*] = ;         // Enemy PEASANTS per cell (open information, 18.09): the goal of
      [*] = ;         // the match is their peasants, and a wave aimed 'at peasants' walks
      [*] = ;         // to the nearest one, which stands under their army. With this grid
      [*] = ;         // next to frow the model can pick a cell where peasants are and
      [*] = ;         // soldiers are not, and send ATTACK target=cell there.
      [*] = ;         var hmpea : array [0..15] of array [0..15] of Integer;
      [*] = ;         // SUMS OF COORDINATES per cell, ours and his apart (27.09, request of
      [*] = ;         // the mac). Why a sixth number in 'cells' is needed at all: by 227 pairs
      [*] = ;         // of snapshots from strike_base and free_peasants, in 218 ticks out of
      [*] = ;         // 445 BOTH sides had five or more fighters in one cell and NOBODY died,
      [*] = ;         // and at equal numbers the losses differ two to three and a half times
      [*] = ;         // (20 ours against 40 his: median 0.63 ours a second, q1 0.60, q3 1.20).
      [*] = ;         // The hidden variable is the distance between the two crowds INSIDE the
      [*] = ;         // cell: the grid quantises to 16 units and the block used to throw the
      [*] = ;         // remainder away. Coordinates are summed here, the centres and their
      [*] = ;         // distance are computed where 'cells' is written.
      [*] = ;         var hmsox : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmsoz : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmsex : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmsez : array [0..15] of array [0..15] of Integer;
      [*] = ;         // HIS ARMY PER CELL, WITH MAKE-UP AND ORDERS (29.09, request of the mac
      [*] = ;         // for the match against a live player). frow gives one mark per cell -
      [*] = ;         // how many, and nothing else - and p<n>_mv_cx/cy give ONE average target
      [*] = ;         // for his whole army. By those two a detachment that charged our
      [*] = ;         // shooters cannot be told from an army standing still: both show a
      [*] = ;         // number in a cell and an average point somewhere between. Counted by
      [*] = ;         // the SAME usage marks as p<n>_inf/_shoot/_cav, so the three sum to
      [*] = ;         // hmforce of that cell and the reader can check it.
      [*] = ;         var hmepk : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmesh : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmecv : array [0..15] of array [0..15] of Integer;
      [*] = ;         // How many of THAT cell are under a move or attack order, and the sum
      [*] = ;         // of their destination cells - the average is taken where ecells is
      [*] = ;         // written. Per cell of the MOVER, not of the target: that is what makes
      [*] = ;         // 'this detachment went for our shooters' sayable.
      [*] = ;         var hmemn : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmetx : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmetz : array [0..15] of array [0..15] of Integer;
      [*] = ;         // TROOPS OF THE 18th CENTURY IN THE CELL (29.09, P8). The usage marks do NOT
      [*] = ;         // separate the centuries - a musketeer17 and a musketeer18 are both 'shooter'
      [*] = ;         // - so the century is read off airole, where the engine keeps its own *18
      [*] = ;         // roles. Written as the LAST column of ecells so every reader of the nine
      [*] = ;         // before it keeps working.
      [*] = ;         var hme18 : array [0..15] of array [0..15] of Integer;
      [*] = ;         // ROLE -> SHORT NAME, one table for BOTH sides (29.09, P6). A chain of ifs
      [*] = ;         // twice over would be thirty lines of the same thing; the pair of arrays is
      [*] = ;         // the form the fighters lists already use in this block and it works.
      [*] = ;         // Declared HERE because both scans below need it, and the enemy scan comes
      [*] = ;         // first: a name used before its declaration kills the tick (15.09).
      [*] = ;         var hbr : array [0..17] of Integer;
      [*] = ;         var hbn : array [0..17] of String;
      [*] = ;         hbr[0]  := gc_ai_unit_center;    hbn[0]  := 'center';
      [*] = ;         hbr[1]  := gc_ai_unit_ba17;      hbn[1]  := 'ba17';
      [*] = ;         hbr[2]  := gc_ai_unit_ba18;      hbn[2]  := 'ba18';
      [*] = ;         hbr[3]  := gc_ai_unit_house;     hbn[3]  := 'house';
      [*] = ;         hbr[4]  := gc_ai_unit_mill;      hbn[4]  := 'mill';
      [*] = ;         hbr[5]  := gc_ai_unit_smith;     hbn[5]  := 'smith';
      [*] = ;         hbr[6]  := gc_ai_unit_store;     hbn[6]  := 'store';
      [*] = ;         hbr[7]  := gc_ai_unit_academi;   hbn[7]  := 'academy';
      [*] = ;         hbr[8]  := gc_ai_unit_minegold;  hbn[8]  := 'minegold';
      [*] = ;         hbr[9]  := gc_ai_unit_mineiron;  hbn[9]  := 'mineiron';
      [*] = ;         hbr[10] := gc_ai_unit_minecoal;  hbn[10] := 'minecoal';
      [*] = ;         hbr[11] := gc_ai_unit_stable;    hbn[11] := 'stable';
      [*] = ;         hbr[12] := gc_ai_unit_tower;     hbn[12] := 'tower';
      [*] = ;         hbr[13] := gc_ai_unit_market;    hbn[13] := 'market';
      [*] = ;         // Four more added after the first live game: TWO of the twenty buildings
      [*] = ;         // the enemy had came out as 'other', and a tenth of his base with no name
      [*] = ;         // is a tenth the enemy model cannot use. These are the rest of what the
      [*] = ;         // engine can place on land.
      [*] = ;         hbr[14] := gc_ai_unit_artdepo;   hbn[14] := 'artdepo';
      [*] = ;         hbr[15] := gc_ai_unit_dipcenter; hbn[15] := 'dipcenter';
      [*] = ;         hbr[16] := gc_ai_unit_temple;    hbn[16] := 'temple';
      [*] = ;         hbr[17] := gc_ai_unit_port;      hbn[17] := 'port';
      [*] = ;         // BUILDINGS OF BOTH SIDES AS A LIST, type and place (29.09, P6). The grid
      [*] = ;         // brow gives one letter per cell and the counters give totals; neither says
      [*] = ;         // WHERE a particular barracks stands, and a cell of 16 units is too coarse
      [*] = ;         // to tell a tight base from a sprawling one. Strings and counters at BLOCK
      [*] = ;         // level: they accumulate across loops, and a scalar declared in a nested
      [*] = ;         // begin does not accumulate in this language (17.09).
      [*] = ;         var hmeb, hmob : String;
      [*] = ;         var hmebn, hmobn, hmeball, hmoball : Integer;
      [*] = ;         // WALLS AND PALISADE BY CELLS (29.09, P7). Checked in the engine, not guessed:
      [*] = ;         // gc_obj_usage_weakwall = 13 is the WOODEN wall - sid ukrwwa/ukrwga, material
      [*] = ;         // woodwall, 10 wood apiece (unit.script:2285-2301) - that is the palisade;
      [*] = ;         // gc_obj_usage_hardwall = 12 is the stone one - sid <nation>swa/sga, 50 stone,
      [*] = ;         // 50000 hp (unit.script:2258-2265). Gates are the same objects with bgate.
      [*] = ;         var hmews : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmewh : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmewg : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmewb : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmewm : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmows : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmowh : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmowg : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmowb : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmowm : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmewseg, hmowseg : Integer;
      [*] = ;         // OUR army per cell with make-up (29.09, P2). mil_inf/_shooters/_cav are
      [*] = ;         // global and 'cells' holds contact cells only and without make-up, so
      [*] = ;         // a bait - shooters in front of pikemen - is invisible on both sides.
      [*] = ;         var hmopk : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmosh : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmocv : array [0..15] of array [0..15] of Integer;
      [*] = ;         var hmi, hmj, hmk, hmpl : Integer;
      [*] = ;         // Counters of OUR army, declared at THIS level on purpose - see the
      [*] = ;         // note where they are zeroed. hmown lives lower and gets away with it
      [*] = ;         // only because it is an array.
      [*] = ;         var hmfx, hmfy, hmfn : Integer;
      [*] = ;         // EXACT NUMBERS FOR CONTACT CELLS (26.09). Declared HERE, at block
      [*] = ;         // level, and not next to the grid writers below: 17.09 six army
      [*] = ;         // counters declared inside a nested begin read as zero at 208
      [*] = ;         // fighters, while the array in the very same place was correct. A
      [*] = ;         // scalar that must ACCUMULATE across a loop belongs at this level.
      [*] = ;         var hmcs : String;
      [*] = ;         var hmcn : Integer;
      [*] = ;         // ecells / ocells and their counters - at THIS level for the same reason
      [*] = ;         // as hmcs/hmcn above: a scalar that accumulates across a loop does not
      [*] = ;         // survive a nested begin in this language (17.09, six counters read zero
      [*] = ;         // at 208 fighters). hmeall/hmoall count ALL cells with fighters, written
      [*] = ;         // out even when the line was cut at 24 - a silent cut would read as
      [*] = ;         // 'his army is nowhere else'.
      [*] = ;         var hmes, hmos : String;
      [*] = ;         var hmen, hmon, hmeall, hmoall, hmband : Integer;
      [*] = ;         var hmwx, hmwy, hmwn : Integer;
      [*] = ;         for hmi := 0 to cHmGrid-1 do
      [*] = ;         for hmj := 0 to cHmGrid-1 do
      [*] = ;         begin
      [*] = ;            hmbase[hmi][hmj] := 0;
      [*] = ;            hmforce[hmi][hmj] := 0;
      [*] = ;            hmdest[hmi][hmj] := 0;
      [*] = ;            hmpea[hmi][hmj] := 0;
      [*] = ;            hmsox[hmi][hmj] := 0;
      [*] = ;            hmsoz[hmi][hmj] := 0;
      [*] = ;            hmsex[hmi][hmj] := 0;
      [*] = ;            hmsez[hmi][hmj] := 0;
      [*] = ;            hmepk[hmi][hmj] := 0;
      [*] = ;            hmesh[hmi][hmj] := 0;
      [*] = ;            hmecv[hmi][hmj] := 0;
      [*] = ;            hmemn[hmi][hmj] := 0;
      [*] = ;            hmetx[hmi][hmj] := 0;
      [*] = ;            hmetz[hmi][hmj] := 0;
      [*] = ;            hmopk[hmi][hmj] := 0;
      [*] = ;            hmosh[hmi][hmj] := 0;
      [*] = ;            hmocv[hmi][hmj] := 0;
      [*] = ;            hme18[hmi][hmj] := 0;
      [*] = ;            hmews[hmi][hmj] := 0;
      [*] = ;            hmewh[hmi][hmj] := 0;
      [*] = ;            hmewg[hmi][hmj] := 0;
      [*] = ;            hmewb[hmi][hmj] := 0;
      [*] = ;            hmows[hmi][hmj] := 0;
      [*] = ;            hmowh[hmi][hmj] := 0;
      [*] = ;            hmowg[hmi][hmj] := 0;
      [*] = ;            hmowb[hmi][hmj] := 0;
      [*] = ;            // The WEAKEST segment of the cell, in percent. 101 means 'no wall here':
      [*] = ;            // a measured 100 and an empty cell must not look the same, and the cell
      [*] = ;            // is only ever written when a wall is in it anyway.
      [*] = ;            hmewm[hmi][hmj] := 101;
      [*] = ;            hmowm[hmi][hmj] := 101;
      [*] = ;         end;
      [*] = ;         // Explicitly, and not by trusting a fresh declaration: hmcs/hmcn next door
      [*] = ;         // are zeroed by hand for the same reason, and a counter that starts from
      [*] = ;         // whatever was there would put a building list of the previous tick into
      [*] = ;         // this one - the quietest kind of wrong.
      [*] = ;         hmeb := '';
      [*] = ;         hmob := '';
      [*] = ;         hmebn := 0;
      [*] = ;         hmobn := 0;
      [*] = ;         hmeball := 0;
      [*] = ;         hmoball := 0;
      [*] = ;         hmewseg := 0;
      [*] = ;         hmowseg := 0;
      [*] = ;         var hmw : Integer = GetMapWidth;
      [*] = ;         var hmh : Integer = GetMapHeight;
      [*] = ;         var hmhw : Integer = hmw div 2;
      [*] = ;         var hmhh : Integer = hmh div 2;
      [*] = ;         var hspl, hsbest : Integer;
      [*] = ;         var hsbestd : Float = 1000000;
      [*] = ;         hsbest := -1;
      [*] = ;         for hspl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;         if (gPlayer[hspl].bexists) and (hspl <> plind) then
      [*] = ;         begin
      [*] = ;            var hsenemy : Boolean = ((gPlayer[plind].enemyPlMask and gPlayer[hspl].myPlMask) <> 0);
      [*] = ;            ParserSetBoolValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_enemy', hsenemy);
      [*] = ;            // WHO IS ON THAT SLOT (29.09, P3). Our own bot sits on a HUMAN slot with
      [*] = ;            // the native ai off, so bhuman alone does not separate a live player from
      [*] = ;            // us - but it does separate both from the native ai, which is what every
      [*] = ;            // container series so far played against. Both flags are written because
      [*] = ;            // together they are unambiguous: player = human and not ai, native ai =
      [*] = ;            // ai and not human. Without this, records of a match against a live
      [*] = ;            // player would be averaged together with 213 runs against the engine.
      [*] = ;            // Same 'p' + index form as every field below, so nothing is pinned to
      [*] = ;            // slot 1: whichever index the player takes, his own key appears.
      [*] = ;            ParserSetBoolValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_human', gMap.players[hspl].bhuman);
      [*] = ;            ParserSetBoolValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_ai', gMap.players[hspl].bai);
      [*] = ;            var hseph : Integer = GetPlayerHandleByIndex(hspl);
      [*] = ;            var hsec : Integer = GetPlayerGameObjectsCountByHandle(hseph);
      [*] = ;            var hsepea, hsebld, hsemil, hsemin, hsj : Integer;
      [*] = ;            var hsxinf, hsxsh, hsxcav, hsegun : Integer;
      [*] = ;            var hsxmg, hsxmi, hsxmc : Integer;
      [*] = ;            var hsxcen, hsxmill, hsxsm, hsxba, hsxba18 : Integer;
      [*] = ;            var hsxstab, hsxstor, hsxho, hsxtow, hsxmar, hsxaca : Integer;
      [*] = ;            // OPEN INFORMATION (18.09): the match is played against another bot
      [*] = ;            // over the network and the new hackathon rules allow everything the
      [*] = ;            // game knows about the opponent. The 'only our own' limits below
      [*] = ;            // are lifted: resources, taken upgrades and training queues of every
      [*] = ;            // other player are read the same way as ours (res[], upgstate[],
      [*] = ;            // produce orders of buildings).
      [*] = ;            var hsytq : String;
      [*] = ;            // Where their soldiers are GOING: move / attackpoint orders carry
      [*] = ;            // the destination in orders[0].info.x/y (lib/unit.script:9458,
      [*] = ;            // player.script:2511), attackobj carries the target handle in
      [*] = ;            // info.trg. Sums of destination cells and how many head for a
      [*] = ;            // point within 60 of OUR town centre. Integers only, like the
      [*] = ;            // counters above - a Float sum here is an untested form.
      [*] = ;            var hsymvn, hsymvb, hsymx, hsymz : Integer;
      [*] = ;            var hsedead : Integer = 0;   // 31.10: his dead objects in the list
      [*] = ;            for hsj := 0 to hsec-1 do
      [*] = ;            begin
      [*] = ;               var hseg : Integer = GetGameObjectHandleByIndex(hsj, hseph);
      [*] = ;               var hsep : Pointer = _unit_GetTObj(hseg);
      [*] = ;               if (hsep<>nil) then
      [*] = ;               if (TObj(hsep).bdead) then
      [*] = ;               hsedead := hsedead + 1;
      [*] = ;               if (hsep<>nil) then
      [*] = ;               // enemy pass (31.10): corpses are not his army, not his peasants, not a camp
      [*] = ;               if (not TObj(hsep).bdead) then
      [*] = ;               begin
      [*] = ;                  var hseu : Integer = gObjProp[TObj(hsep).cid][TObj(hsep).id].usage;
      [*] = ;                  if (hseu = gc_obj_usage_peasant) then
      [*] = ;                  hsepea := hsepea + 1;
      [*] = ;                  // Army of the enemy, counted by the SAME usage marks as our own
      [*] = ;                  // (mil_inf/mil_shooters/mil_cav above). The player said 16.09 he
      [*] = ;                  // sees the enemy base, army, peasants and mines on an open map,
      [*] = ;                  // so this is not a head start - it is what the human already has.
      [*] = ;                  // ONE flag for both counters below. It used to be a bare
      [*] = ;                  // single-statement if guarding hsemil only, and the force
      [*] = ;                  // grid right after it ran for EVERY enemy object - peasants
      [*] = ;                  // and buildings included. Live game 16.09 caught it by
      [*] = ;                  // arithmetic: p1_army = 0 while the grid showed 7+5+9 = 21,
      [*] = ;                  // and the enemy had exactly 19 peasants and 2 buildings.
      [*] = ;                  // The map is labelled "enemy soldiers" - it must count those.
      [*] = ;                  var hsefight : Boolean = False;
      [*] = ;                  if (hseu = gc_obj_usage_lightinfantry) or (hseu = gc_obj_usage_weak) or
      [*] = ;                     (hseu = gc_obj_usage_grenadier) or (hseu = gc_obj_usage_shooter) or
      [*] = ;                     (hseu = gc_obj_usage_archer) or (hseu = gc_obj_usage_fasthorse) or
      [*] = ;                     (hseu = gc_obj_usage_hardhorse) or (hseu = gc_obj_usage_horseshooter) then
      [*] = ;                  hsefight := True;
      [*] = ;                  // Artillery counted APART from the rest: in the readiness the
      [*] = ;                  // player asked for it stands with a MINUS, and a battery of
      [*] = ;                  // four is not the same threat as four musketeers. The engine
      [*] = ;                  // knows four kinds, all of them guns.
      [*] = ;                  if (hseu = gc_obj_usage_cannon) or (hseu = gc_obj_usage_mcannon) or
      [*] = ;                     (hseu = gc_obj_usage_mortar) or (hseu = gc_obj_usage_supermortar) then
      [*] = ;                  hsegun := hsegun + 1;
      [*] = ;                  if (hsefight) then
      [*] = ;                  hsemil := hsemil + 1;
      [*] = ;                  if (hsenemy) and (hsefight) then
      [*] = ;                  begin
      [*] = ;                     var hmux : Integer = floor((GetGameObjectPositionXByHandle(hseg)+hmhw)*cHmGrid/hmw);
      [*] = ;                     var hmuy : Integer = floor((GetGameObjectPositionZByHandle(hseg)+hmhh)*cHmGrid/hmh);
      [*] = ;                     if (hmux>=0) and (hmux<cHmGrid) and (hmuy>=0) and (hmuy<cHmGrid) then
      [*] = ;                     begin
      [*] = ;                        hmforce[hmux][hmuy] := hmforce[hmux][hmuy] + 1;
      [*] = ;                        hmsex[hmux][hmuy] := hmsex[hmux][hmuy] + Round(GetGameObjectPositionXByHandle(hseg)+hmhw);
      [*] = ;                        hmsez[hmux][hmuy] := hmsez[hmux][hmuy] + Round(GetGameObjectPositionZByHandle(hseg)+hmhh);
      [*] = ;                        // MAKE-UP OF THIS CELL (29.09, P1). The three marks split
      [*] = ;                        // hsefight exactly, so hmepk+hmesh+hmecv = hmforce of the
      [*] = ;                        // cell - the reader can check the block by arithmetic, the
      [*] = ;                        // way the live game caught the force grid counting peasants
      [*] = ;                        // on 16.09. A flag is NOT needed here: each if is its own
      [*] = ;                        // one-line statement and nothing is appended after it.
      [*] = ;                        if (hseu = gc_obj_usage_lightinfantry) or (hseu = gc_obj_usage_weak) or
      [*] = ;                           (hseu = gc_obj_usage_grenadier) then
      [*] = ;                        hmepk[hmux][hmuy] := hmepk[hmux][hmuy] + 1;
      [*] = ;                        if (hseu = gc_obj_usage_shooter) or (hseu = gc_obj_usage_archer) then
      [*] = ;                        hmesh[hmux][hmuy] := hmesh[hmux][hmuy] + 1;
      [*] = ;                        if (hseu = gc_obj_usage_fasthorse) or (hseu = gc_obj_usage_hardhorse) or
      [*] = ;                           (hseu = gc_obj_usage_horseshooter) then
      [*] = ;                        hmecv[hmux][hmuy] := hmecv[hmux][hmuy] + 1;
      [*] = ;                        // Century by ROLE, not by usage - usage knows nothing about it.
      [*] = ;                        // Officer18 and drummer18 are counted here too: unlike the
      [*] = ;                        // figures line, this column answers 'where are his new troops',
      [*] = ;                        // and a drummer marching with them is one of them.
      [*] = ;                        var hse18 : Integer = gObjProp[TObj(hsep).cid][TObj(hsep).id].airole;
      [*] = ;                        if (hse18 = gc_ai_unit_pikeman18) or (hse18 = gc_ai_unit_musk18) or
      [*] = ;                           (hse18 = gc_ai_unit_dragun18) or (hse18 = gc_ai_unit_uniq_inf18) or
      [*] = ;                           (hse18 = gc_ai_unit_uniq_cav18) or (hse18 = gc_ai_unit_officer18) or
      [*] = ;                           (hse18 = gc_ai_unit_drummer18) then
      [*] = ;                        hme18[hmux][hmuy] := hme18[hmux][hmuy] + 1;
      [*] = ;                     end;
      [*] = ;                     var hseot : Integer = TObj(hsep).orders[0].itype;
      [*] = ;                     var hsytx : Float = -1000000;
      [*] = ;                     var hsytz : Float = -1000000;
      [*] = ;                     if (hseot = gc_obj_order_type_move) or (hseot = gc_obj_order_type_attackpoint) or
      [*] = ;                        (hseot = gc_obj_order_type_continueattackpoint) then
      [*] = ;                     begin
      [*] = ;                        hsytx := TObj(hsep).orders[0].info.x;
      [*] = ;                        hsytz := TObj(hsep).orders[0].info.y;
      [*] = ;                     end;
      [*] = ;                     if (hseot = gc_obj_order_type_attackobj) then
      [*] = ;                     if (TObj(hsep).orders[0].info.trg <> 0) then
      [*] = ;                     begin
      [*] = ;                        hsytx := GetGameObjectPositionXByHandle(TObj(hsep).orders[0].info.trg);
      [*] = ;                        hsytz := GetGameObjectPositionZByHandle(TObj(hsep).orders[0].info.trg);
      [*] = ;                     end;
      [*] = ;                     if (hsytx > -999999) then
      [*] = ;                     begin
      [*] = ;                        hsymvn := hsymvn + 1;
      [*] = ;                        hsymx := hsymx + floor((hsytx+hmhw)*cHmGrid/hmw);
      [*] = ;                        hsymz := hsymz + floor((hsytz+hmhh)*cHmGrid/hmh);
      [*] = ;                        var hmdx : Integer = floor((hsytx+hmhw)*cHmGrid/hmw);
      [*] = ;                        var hmdy : Integer = floor((hsytz+hmhh)*cHmGrid/hmh);
      [*] = ;                        if (hmdx>=0) and (hmdx<cHmGrid) and (hmdy>=0) and (hmdy<cHmGrid) then
      [*] = ;                        hmdest[hmdx][hmdy] := hmdest[hmdx][hmdy] + 1;
      [*] = ;                        // THE SAME DESTINATION, KEPT BY THE CELL HE STANDS IN (29.09,
      [*] = ;                        // P1). hmdest above is indexed by the TARGET cell and loses
      [*] = ;                        // who is walking there from where; that is the very thing
      [*] = ;                        // needed to tell a charge from a retreat. Both cells are
      [*] = ;                        // range-checked, so the sum of hmemn over the grid equals
      [*] = ;                        // the sum of hmdest - two readings of one fact that must
      [*] = ;                        // agree. Nested one-line ifs before a begin: the same form
      [*] = ;                        // the attackobj gate above uses and the live game proved.
      [*] = ;                        if (hmdx>=0) and (hmdx<cHmGrid) and (hmdy>=0) and (hmdy<cHmGrid) then
      [*] = ;                        if (hmux>=0) and (hmux<cHmGrid) and (hmuy>=0) and (hmuy<cHmGrid) then
      [*] = ;                        begin
      [*] = ;                           hmemn[hmux][hmuy] := hmemn[hmux][hmuy] + 1;
      [*] = ;                           hmetx[hmux][hmuy] := hmetx[hmux][hmuy] + hmdx;
      [*] = ;                           hmetz[hmux][hmuy] := hmetz[hmux][hmuy] + hmdy;
      [*] = ;                        end;
      [*] = ;                        if (hscen > 0) then
      [*] = ;                        if (VectorDistance(hsytx, 0, hsytz, hscx, 0, hscz) < 60) then
      [*] = ;                        hsymvb := hsymvb + 1;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hsenemy) and (hseu = gc_obj_usage_peasant) then
      [*] = ;                  begin
      [*] = ;                     var hmpx : Integer = floor((GetGameObjectPositionXByHandle(hseg)+hmhw)*cHmGrid/hmw);
      [*] = ;                     var hmpy : Integer = floor((GetGameObjectPositionZByHandle(hseg)+hmhh)*cHmGrid/hmh);
      [*] = ;                     if (hmpx>=0) and (hmpx<cHmGrid) and (hmpy>=0) and (hmpy<cHmGrid) then
      [*] = ;                     hmpea[hmpx][hmpy] := hmpea[hmpx][hmpy] + 1;
      [*] = ;                  end;
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
      [*] = ;                     // HIS BUILDINGS AS A LIST and HIS WALLS BY CELLS (29.09, P6/P7).
      [*] = ;                     // Only for a player we are at war with: a neutral's yard is not
      [*] = ;                     // what the enemy model is being fitted to, and the grids above
      [*] = ;                     // are gated the same way.
      [*] = ;                     if (hsenemy) then
      [*] = ;                     begin
      [*] = ;                        var hbu : Integer = gObjProp[TObj(hsep).cid][TObj(hsep).id].usage;
      [*] = ;                        var hbx : Integer = Round(GetGameObjectPositionXByHandle(hseg)) + hmhw;
      [*] = ;                        var hbz : Integer = Round(GetGameObjectPositionZByHandle(hseg)) + hmhh;
      [*] = ;                        var hbmax : Integer = gPlayer[hspl].objbase[TObj(hsep).cid][TObj(hsep).id].maxhp;
      [*] = ;                        var hbpct : Integer = 100;
      [*] = ;                        if (hbmax > 0) then
      [*] = ;                        hbpct := Round((TObj(hsep).hp * 100) / hbmax);
      [*] = ;                        var hbdone : Integer = 0;
      [*] = ;                        if (TObj(hsep).bbuilt) then
      [*] = ;                        hbdone := 1;
      [*] = ;                        if (hbu = gc_obj_usage_hardwall) or (hbu = gc_obj_usage_weakwall) then
      [*] = ;                        begin
      [*] = ;                           // A wall is a building too, and it must NOT land in ebuild:
      [*] = ;                           // a palisade of eighty segments would crowd out the barracks
      [*] = ;                           // the list is for. It goes on its own grid instead.
      [*] = ;                           hmewseg := hmewseg + 1;
      [*] = ;                           var hbcx : Integer = floor(hbx*cHmGrid/hmw);
      [*] = ;                           var hbcy : Integer = floor(hbz*cHmGrid/hmh);
      [*] = ;                           if (hbcx>=0) and (hbcx<cHmGrid) and (hbcy>=0) and (hbcy<cHmGrid) then
      [*] = ;                           begin
      [*] = ;                              if (hbu = gc_obj_usage_weakwall) then
      [*] = ;                              hmews[hbcx][hbcy] := hmews[hbcx][hbcy] + 1;
      [*] = ;                              if (hbu = gc_obj_usage_hardwall) then
      [*] = ;                              hmewh[hbcx][hbcy] := hmewh[hbcx][hbcy] + 1;
      [*] = ;                              if (gObjProp[TObj(hsep).cid][TObj(hsep).id].bgate) then
      [*] = ;                              hmewg[hbcx][hbcy] := hmewg[hbcx][hbcy] + 1;
      [*] = ;                              if (hbdone = 0) then
      [*] = ;                              hmewb[hbcx][hbcy] := hmewb[hbcx][hbcy] + 1;
      [*] = ;                              if (hbpct < hmewm[hbcx][hbcy]) then
      [*] = ;                              hmewm[hbcx][hbcy] := hbpct;
      [*] = ;                           end;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           hmeball := hmeball + 1;
      [*] = ;                           if (hmebn < 60) then
      [*] = ;                           begin
      [*] = ;                              var hbname : String = 'other';
      [*] = ;                              var hbk : Integer;
      [*] = ;                              for hbk := 0 to 17 do
      [*] = ;                              if (hbr[hbk] = gObjProp[TObj(hsep).cid][TObj(hsep).id].airole) then
      [*] = ;                              hbname := hbn[hbk];
      [*] = ;                              if (hmebn > 0) then
      [*] = ;                              hmeb := hmeb + ';';
      [*] = ;                              hmeb := hmeb + hbname + ',' + IntToStr(hbx) + ',' + IntToStr(hbz) +
      [*] = ;                                   ',' + IntToStr(hbdone) + ',' + IntToStr(hbpct);
      [*] = ;                              hmebn := hmebn + 1;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     // What this building of theirs is making: same reading as
      [*] = ;                     // our train_now (produce orders, info.produceid, info.amount).
      [*] = ;                     var hsyk : Integer;
      [*] = ;                     for hsyk := 0 to gc_obj_MaxOrderCount-1 do
      [*] = ;                     begin
      [*] = ;                        var hsyp : Pointer = TObj(hsep).orders[hsyk];
      [*] = ;                        if (hsyp<>nil) then
      [*] = ;                        if (TOrder(hsyp).itype = gc_obj_order_type_produce) then
      [*] = ;                        begin
      [*] = ;                           if (hsytq <> '') then hsytq := hsytq + ',';
      [*] = ;                           hsytq := hsytq + gCountry[TObj(hsep).cid].members[TOrder(hsyp).info.produceid] + ':';
      [*] = ;                           if (TOrder(hsyp).info.amount = gc_obj_order_produce_infinite) then
      [*] = ;                           hsytq := hsytq + 'inf'
      [*] = ;                           else
      [*] = ;                           hsytq := hsytq + IntToStr(TOrder(hsyp).info.amount);
      [*] = ;                        end;
      [*] = ;                     end;
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
      [*] = ;            // LOSSES FROM THE ENGINE'S OWN STATISTICS (20.09). gPlayer[pl].stat.killed[cid][id]
      [*] = ;            // is incremented in _unit_RemoveObjFromPlayerCounters (lib/unit.script:3900) for
      [*] = ;            // the OWNER of the dead unit, capture excluded - so for player hspl it is how
      [*] = ;            // many of HIS units of that type have died. The peasant counter alone could not
      [*] = ;            // tell a kill from a peasant walking into a mine: 20.09 our wave stood seven
      [*] = ;            // cells away and his count fell 23 -> 16, and the bridge called it a milestone.
      [*] = ;            // Here the engine says how many of his peasants and fighters really died.
      [*] = ;            var hselc : Integer = gPlayer[hspl].cid;
      [*] = ;            var hselp, hselm, hselk : Integer;
      [*] = ;            for hselk := 0 to gc_country_maxmembers-1 do
      [*] = ;            begin
      [*] = ;               var hselu : Integer = gObjProp[hselc][hselk].usage;
      [*] = ;               if (hselu = gc_obj_usage_peasant) then
      [*] = ;               hselp := hselp + gPlayer[hspl].stat.killed[hselc][hselk];
      [*] = ;               if (hselu = gc_obj_usage_lightinfantry) or (hselu = gc_obj_usage_weak) or (hselu = gc_obj_usage_grenadier) or
      [*] = ;                  (hselu = gc_obj_usage_shooter) or (hselu = gc_obj_usage_archer) or (hselu = gc_obj_usage_fasthorse) or
      [*] = ;                  (hselu = gc_obj_usage_hardhorse) or (hselu = gc_obj_usage_horseshooter) then
      [*] = ;               hselm := hselm + gPlayer[hspl].stat.killed[hselc][hselk];
      [*] = ;            end;
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_pea_lost', hselp);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mil_lost', hselm);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_peasants', hsepea);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_bldgs',    hsebld);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_army',     hsemil);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mines',    hsemin);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_inf',      hsxinf);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_shoot',    hsxsh);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_cav',      hsxcav);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_guns',     hsegun);
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
      [*] = ;            // Their resources, read exactly as our own six lines at the top.
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_food',  not gPlayer[hspl].res[gc_resource_type_food]);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_wood',  not gPlayer[hspl].res[gc_resource_type_wood]);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_stone', not gPlayer[hspl].res[gc_resource_type_stone]);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_gold',  not gPlayer[hspl].res[gc_resource_type_gold]);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_iron',  not gPlayer[hspl].res[gc_resource_type_iron]);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_coal',  not gPlayer[hspl].res[gc_resource_type_coal]);
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_train', hsytq);
      [*] = ;            // Their upgrades ALREADY TAKEN: upgstate[cid][i].done of their own
      [*] = ;            // nation's list, names without the 3-letter nation prefix, as in
      [*] = ;            // upg_done below. The 'only our own' note there is history now.
      [*] = ;            var hsyud : String;
      [*] = ;            var hsyui : Integer;
      [*] = ;            var hsycid : Integer = gPlayer[hspl].cid;
      [*] = ;            for hsyui := 0 to gc_country_maxupgradecount-1 do
      [*] = ;            begin
      [*] = ;               var hsyus : String = gCountry[hsycid].upgrade[hsyui].id;
      [*] = ;               if (StrLength(hsyus) > 3) then
      [*] = ;               if (gPlayer[hspl].upgstate[hsycid][hsyui].done) then
      [*] = ;               begin
      [*] = ;                  if (StrLength(hsyud) > 0) then hsyud := hsyud + ',';
      [*] = ;                  hsyud := hsyud + SubStr(hsyus, 4, StrLength(hsyus)-3);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_upg_done', hsyud);
      [*] = ;            // HIS fighters in NUMBERS, upgrades included. objbase is kept PER PLAYER
      [*] = ;            // (player.script:1798), so his figures are read exactly like ours above -
      [*] = ;            // only the player index differs. Until 19.09 the model saw WHICH upgrades he
      [*] = ;            // took (p<n>_upg_done) but not WHAT they gave, while her own numbers came
      [*] = ;            // with atk/dpike from the unit card: she could not compare her pikeman with
      [*] = ;            // his. On an open map a human reads the same figures off the enemy unit card,
      [*] = ;            // so this is not a head start.
      [*] = ;            // Own role lists, NOT the ones used for our own fighters far above: reusing
      [*] = ;            // a name across a closed block is how the tick died on 15.09.
      [*] = ;            // TYPES OF THE 18th CENTURY ADDED 29.09 (P8 of the mac). Without their
      [*] = ;            // figures the combat law counts a musketeer18 by the numbers of a
      [*] = ;            // musketeer17 and is simply wrong about him. Roles are the engine's own
      [*] = ;            // (dmscript.global): musk18 29, dragun18 38, uniq_inf18 45, uniq_cav18 47,
      [*] = ;            // pikeman18 54. Officer18 and drummer18 are NOT here on purpose: they are
      [*] = ;            // support, they stand outside p<n>_inf/_shoot/_cav, and the law needs
      [*] = ;            // attack and protection, which a drummer does not carry.
      [*] = ;            var hsyfr : array [0..8] of Integer;
      [*] = ;            var hsyfn : array [0..8] of String;
      [*] = ;            hsyfr[0] := gc_ai_unit_infantry17;  hsyfn[0] := 'infantry17';
      [*] = ;            hsyfr[1] := gc_ai_unit_musk17;      hsyfn[1] := 'musk17';
      [*] = ;            hsyfr[2] := gc_ai_unit_uniq_inf17;  hsyfn[2] := 'uniq_inf17';
      [*] = ;            hsyfr[3] := gc_ai_unit_dragoon17;   hsyfn[3] := 'dragoon17';
      [*] = ;            hsyfr[4] := gc_ai_unit_pikeman18;   hsyfn[4] := 'pikeman18';
      [*] = ;            hsyfr[5] := gc_ai_unit_musk18;      hsyfn[5] := 'musk18';
      [*] = ;            hsyfr[6] := gc_ai_unit_dragun18;    hsyfn[6] := 'dragun18';
      [*] = ;            hsyfr[7] := gc_ai_unit_uniq_inf18;  hsyfn[7] := 'uniq_inf18';
      [*] = ;            hsyfr[8] := gc_ai_unit_uniq_cav18;  hsyfn[8] := 'uniq_cav18';
      [*] = ;            var hsyftxt : String = '';
      [*] = ;            var hsyfi : Integer;
      [*] = ;            for hsyfi := 0 to 8 do
      [*] = ;            begin
      [*] = ;               var hsyfid : Integer = -1;
      [*] = ;               var hsyfj : Integer;
      [*] = ;               for hsyfj := 0 to gc_country_maxmembers-1 do
      [*] = ;               if (hsyfid < 0) and (gObjProp[hsycid][hsyfj].airole = hsyfr[hsyfi]) then
      [*] = ;               hsyfid := hsyfj;
      [*] = ;               if (hsyfid >= 0) then
      [*] = ;               begin
      [*] = ;                  // Attack is the BEST weapon slot, not slot 0: the musketeer keeps his
      [*] = ;                  // shot in another slot, and slot 0 reported atk0 on a live game 16.09.
      [*] = ;                  var hsyfa, hsyfwi, hsyfwb : Integer;
      [*] = ;                  hsyfa := 0;
      [*] = ;                  hsyfwb := -1;
      [*] = ;                  for hsyfwi := 0 to gc_obj_MaxWeapon-1 do
      [*] = ;                  if (gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwi].damage > hsyfa) then
      [*] = ;                  begin
      [*] = ;                     hsyfa := gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwi].damage;
      [*] = ;                     hsyfwb := hsyfwi;
      [*] = ;                  end;
      [*] = ;                  hsyftxt := hsyftxt + hsyfn[hsyfi] + '=hp' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].maxhp);
      [*] = ;                  hsyftxt := hsyftxt + ',atk' + IntToStr(hsyfa);
      [*] = ;                  if (hsyfwb >= 0) then
      [*] = ;                  begin
      [*] = ;                     hsyftxt := hsyftxt + ',wkind' + IntToStr(gObjProp[hsycid][hsyfid].weapon[hsyfwb].kind);
      [*] = ;                     hsyftxt := hsyftxt + ',pause' + IntToStr(Round(gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwb].pause*100));
      [*] = ;                     hsyftxt := hsyftxt + ',rmax' + IntToStr(Round(gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwb].radiusmax*100));
      [*] = ;                     // The same two terms for HIS fighters, same slot, same reason.
      [*] = ;
      [*] = ;                     hsyftxt := hsyftxt + ',dmgs' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwb].damagestatic);
      [*] = ;                     hsyftxt := hsyftxt + ',dmgp' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwb].damagepercent);
      [*] = ;                     hsyftxt := hsyftxt + ',dinit' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].weapon[hsyfwb].damageinit);
      [*] = ;                  end;
      [*] = ;                  hsyftxt := hsyftxt + ',dpike' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].protection[gc_obj_weapon_kind_pike]);
      [*] = ;                  hsyftxt := hsyftxt + ',dsword' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].protection[gc_obj_weapon_kind_sword]);
      [*] = ;                  hsyftxt := hsyftxt + ',dbullet' + IntToStr(gPlayer[hspl].objbase[hsycid][hsyfid].protection[gc_obj_weapon_kind_bullet]);
      [*] = ;                  hsyftxt := hsyftxt + ' ';
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // Always write the key, even empty: a missing line and 'none' look the same
      [*] = ;            // from Python (14.09, a round lost to guessing which it was).
      [*] = ;            if (hsyftxt = '') then
      [*] = ;            hsyftxt := 'none-found';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_fighters', hsyftxt);
      [*] = ;            // HIS SQUADS (24.09, idea/formation). The calculator overrated us THREEFOLD
      [*] = ;            // in 329 recorded fights, and the missing term is the formation: an officer
      [*] = ;            // squad gets fAddDamage/fAddShield (miscext2.script:428, :351), the LINE
      [*] = ;            // shapes give +2/+2 marching and +7/+7 holding (formations.cfg). He trains
      [*] = ;            // officers in 40 games of 52. Read like our own squads far above, own names.
      [*] = ;            // LIVE GAME 25.09 (Windows, 915 s): the count and the largest squad were right
      [*] = ;            // (1 -> 5 squads, 36 men), but the shape was read off the LARGEST squad, and
      [*] = ;            // that one is the officerless crowd with fFormation -1: the shape fields never
      [*] = ;            // appeared while an officer stood on the field. So the shape is now taken from
      [*] = ;            // the squads that HAVE a bonus shape: how many there are, how many of them
      [*] = ;            // hold, and the best one (largest bonus, then largest squad).
      [*] = ;            var hsysqn : Integer = gPlayer[hspl].squads.GetCount;
      [*] = ;            var hsysqu, hsysqi, hsysqh, hsysqfn, hsysqfh, hsysqbb, hsysqbu : Integer;
      [*] = ;            var hsysqf : Integer = -1;
      [*] = ;            for hsysqi := 0 to hsysqn-1 do
      [*] = ;            begin
      [*] = ;               var hsypsq : Pointer = gPlayer[hspl].squads.Get(hsysqi);
      [*] = ;               if (hsypsq<>nil) then
      [*] = ;               begin
      [*] = ;                  if (TSquad(hsypsq).fHoldMode) then
      [*] = ;                  hsysqh := hsysqh + 1;
      [*] = ;                  if (TSquad(hsypsq).GetCount > hsysqu) then
      [*] = ;                  hsysqu := TSquad(hsypsq).GetCount;
      [*] = ;                  var hsyff : Integer = TSquad(hsypsq).fFormation;
      [*] = ;                  if (hsyff >= 0) then
      [*] = ;                  begin
      [*] = ;                     var hsyfb : Integer = gFormation[hsyff].bonusdamage + gFormation[hsyff].bonusshield +
      [*] = ;                          gFormation[hsyff].bonusdamagehold + gFormation[hsyff].bonusshieldhold;
      [*] = ;                     if (hsyfb > 0) then
      [*] = ;                     begin
      [*] = ;                        hsysqfn := hsysqfn + 1;
      [*] = ;                        if (TSquad(hsypsq).fHoldMode) then
      [*] = ;                        hsysqfh := hsysqfh + 1;
      [*] = ;                        if (hsyfb > hsysqbb) or ((hsyfb = hsysqbb) and (TSquad(hsypsq).GetCount > hsysqbu)) then
      [*] = ;                        begin
      [*] = ;                           hsysqbb := hsyfb;
      [*] = ;                           hsysqbu := TSquad(hsypsq).GetCount;
      [*] = ;                           hsysqf := hsyff;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squads', hsysqn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_dead', hsedead);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_units', hsysqu);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_hold', hsysqh);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squads_form', hsysqfn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squads_form_hold', hsysqfh);
      [*] = ;            if (hsysqf >= 0) then
      [*] = ;            begin
      [*] = ;               ParserSetValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_form', gFormation[hsysqf].sid);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_form_units', hsysqbu);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_dmg', gFormation[hsysqf].bonusdamage);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_def', gFormation[hsysqf].bonusshield);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_hdmg', gFormation[hsysqf].bonusdamagehold);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_squad_hdef', gFormation[hsysqf].bonusshieldhold);
      [*] = ;            end;
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mv_n', hsymvn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mv_base', hsymvb);
      [*] = ;            if (hsymvn > 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mv_cx', hsymx div hsymvn);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'p' + IntToStr(hspl) + '_mv_cy', hsymz div hsymvn);
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         if (hsbest >= 0) then
      [*] = ;         ParserSetIntValueByKeyByHandle(hsp, 'en_near_dist', Round(hsbestd));
      [*] = ;         // Buildings of every player, binned into cells. The engine keeps a
      [*] = ;         // ready list per player, which is cheaper than walking all objects.
      [*] = ;         for hmpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;         if (gPlayer[hmpl].bexists) then
      [*] = ;         begin
      [*] = ;            var hmcode : Integer = 1;
      [*] = ;            if (hmpl = plind) then
      [*] = ;            hmcode := 2
      [*] = ;            else
      [*] = ;            if ((gPlayer[plind].enemyPlMask and gPlayer[hmpl].myPlMask) <> 0) then
      [*] = ;            hmcode := 3;
      [*] = ;            for hmk := 0 to gPlayer[hmpl].lists.buildings.GetCount-1 do
      [*] = ;            begin
      [*] = ;               var hmbh : Integer = gPlayer[hmpl].lists.buildings.Get(hmk);
      [*] = ;               var hmbcx : Integer = floor((GetGameObjectPositionXByHandle(hmbh)+hmhw)*cHmGrid/hmw);
      [*] = ;               var hmbcy : Integer = floor((GetGameObjectPositionZByHandle(hmbh)+hmhh)*cHmGrid/hmh);
      [*] = ;               if (hmbcx>=0) and (hmbcx<cHmGrid) and (hmbcy>=0) and (hmbcy<cHmGrid) then
      [*] = ;               if (hmbase[hmbcx][hmbcy] < hmcode) then
      [*] = ;               hmbase[hmbcx][hmbcy] := hmcode;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 8);
      [*] = ;         // The grid goes out ONLY when a town center exists: without it there
      [*] = ;         // is no anchor and the 'my base' cell would be a lie. No grid_n key
      [*] = ;         // means python says nothing about the map at all.
      [*] = ;         if (hscen > 0) then
      [*] = ;         begin
      [*] = ;            var hmcx : Integer = floor((hscx+hmhw)*cHmGrid/hmw);
      [*] = ;            var hmcy : Integer = floor((hscz+hmhh)*cHmGrid/hmh);
      [*] = ;            if (hmcx<0) then hmcx := 0;
      [*] = ;            if (hmcx>cHmGrid-1) then hmcx := cHmGrid-1;
      [*] = ;            if (hmcy<0) then hmcy := 0;
      [*] = ;            if (hmcy>cHmGrid-1) then hmcy := cHmGrid-1;
      [*] = ;            hmbase[hmcx][hmcy] := 4;
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'grid_n', cHmGrid);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'my_cx',  hmcx);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'my_cy',  hmcy);
      [*] = ;            // OUR OWN fighters on the SAME grid. Until 17.09 the map showed the enemy
      [*] = ;            // only: the model saw where he stands and not where its own fist is, so
      [*] = ;            // there was nothing to command with, and in 644 ticks it never mentioned
      [*] = ;            // a single cell. ONE grid, not two: the minimap already costs about 410
      [*] = ;            // tokens a tick, a third of the whole state, and a second would double it.
      [*] = ;            var hmown : array [0..15] of array [0..15] of Integer;
      [*] = ;            for hmi := 0 to cHmGrid-1 do
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            hmown[hmi][hmj] := 0;
      [*] = ;            // Zeroed HERE, declared OUTSIDE (next to hmbase/hmforce). Live game
      [*] = ;            // 17.09 showed why: declared inside this block they never accumulated
      [*] = ;            // - 208 soldiers stood in the grid and both counters read zero, while
      [*] = ;            // the hmown ARRAY, declared in the very same place, was correct all
      [*] = ;            // along. An array survives by reference, a scalar does not; hsfree
      [*] = ;            // works because it is declared at the top of the block, like these now.
      [*] = ;            hmfx := 0;
      [*] = ;            hmfy := 0;
      [*] = ;            hmfn := 0;
      [*] = ;            hmwx := 0;
      [*] = ;            hmwy := 0;
      [*] = ;            hmwn := 0;
      [*] = ;            var hmok : Integer;
      [*] = ;            for hmok := 0 to hscount-1 do
      [*] = ;            begin
      [*] = ;               var hmog : Integer = GetGameObjectHandleByIndex(hmok, hsph);
      [*] = ;               var hmop : Pointer = _unit_GetTObj(hmog);
      [*] = ;               if (hmop<>nil) then
      [*] = ;               if (not gObjProp[TObj(hmop).cid][TObj(hmop).id].bbuilding) then
      [*] = ;               begin
      [*] = ;                  var hmou : Integer = gObjProp[TObj(hmop).cid][TObj(hmop).id].usage;
      [*] = ;                  var hmof : Boolean = False;
      [*] = ;                  if (hmou = gc_obj_usage_lightinfantry) or (hmou = gc_obj_usage_weak) or
      [*] = ;                     (hmou = gc_obj_usage_grenadier) or (hmou = gc_obj_usage_shooter) or
      [*] = ;                     (hmou = gc_obj_usage_archer) or (hmou = gc_obj_usage_fasthorse) or
      [*] = ;                     (hmou = gc_obj_usage_hardhorse) or (hmou = gc_obj_usage_horseshooter) then
      [*] = ;                  hmof := True;
      [*] = ;                  // The flag is DELIBERATE: nothing may be appended after a one-line if in
      [*] = ;                  // this language - the statement lands outside the condition. On 16.09 the
      [*] = ;                  // force grid counted peasants and buildings along with the soldiers that way.
      [*] = ;                  if (hmof) then
      [*] = ;                  begin
      [*] = ;                     var hmoxx : Integer = floor((GetGameObjectPositionXByHandle(hmog)+hmhw)*cHmGrid/hmw);
      [*] = ;                     var hmoyy : Integer = floor((GetGameObjectPositionZByHandle(hmog)+hmhh)*cHmGrid/hmh);
      [*] = ;                     if (hmoxx>=0) and (hmoxx<cHmGrid) and (hmoyy>=0) and (hmoyy<cHmGrid) then
      [*] = ;                     begin
      [*] = ;                        hmown[hmoxx][hmoyy] := hmown[hmoxx][hmoyy] + 1;
      [*] = ;                        hmsox[hmoxx][hmoyy] := hmsox[hmoxx][hmoyy] + Round(GetGameObjectPositionXByHandle(hmog)+hmhw);
      [*] = ;                        hmsoz[hmoxx][hmoyy] := hmsoz[hmoxx][hmoyy] + Round(GetGameObjectPositionZByHandle(hmog)+hmhh);
      [*] = ;                        // OUR make-up in this cell (29.09, P2), by the same marks as
      [*] = ;                        // mil_inf/mil_shooters/mil_cav, so the three sum to hmown of
      [*] = ;                        // the cell.
      [*] = ;                        if (hmou = gc_obj_usage_lightinfantry) or (hmou = gc_obj_usage_weak) or
      [*] = ;                           (hmou = gc_obj_usage_grenadier) then
      [*] = ;                        hmopk[hmoxx][hmoyy] := hmopk[hmoxx][hmoyy] + 1;
      [*] = ;                        if (hmou = gc_obj_usage_shooter) or (hmou = gc_obj_usage_archer) then
      [*] = ;                        hmosh[hmoxx][hmoyy] := hmosh[hmoxx][hmoyy] + 1;
      [*] = ;                        if (hmou = gc_obj_usage_fasthorse) or (hmou = gc_obj_usage_hardhorse) or
      [*] = ;                           (hmou = gc_obj_usage_horseshooter) then
      [*] = ;                        hmocv[hmoxx][hmoyy] := hmocv[hmoxx][hmoyy] + 1;
      [*] = ;                        // The fist at home and the wave in the field are counted APART: only free
      [*] = ;                        // men can be sent, and the model must see where exactly they stand.
      [*] = ;                        if (TObj(hmop).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                        begin
      [*] = ;                           hmfx := hmfx + hmoxx;
      [*] = ;                           hmfy := hmfy + hmoyy;
      [*] = ;                           hmfn := hmfn + 1;
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           hmwx := hmwx + hmoxx;
      [*] = ;                           hmwy := hmwy + hmoyy;
      [*] = ;                           hmwn := hmwn + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               // OUR BUILDINGS AS A LIST and OUR WALLS BY CELLS (29.09, P6/P7). The
      [*] = ;               // branch above took only NON-buildings; this one takes the rest, in the
      [*] = ;               // same pass over the same objects. A SECOND `if (hmop<>nil)` on purpose:
      [*] = ;               // nothing may be appended after the closed begin of a one-line if, and
      [*] = ;               // an else here would have to hang off the nil test, not the building one.
      [*] = ;               if (hmop<>nil) then
      [*] = ;               if (gObjProp[TObj(hmop).cid][TObj(hmop).id].bbuilding) then
      [*] = ;               begin
      [*] = ;                  var hou : Integer = gObjProp[TObj(hmop).cid][TObj(hmop).id].usage;
      [*] = ;                  var hox : Integer = Round(GetGameObjectPositionXByHandle(hmog)) + hmhw;
      [*] = ;                  var hoz : Integer = Round(GetGameObjectPositionZByHandle(hmog)) + hmhh;
      [*] = ;                  var homax : Integer = gPlayer[plind].objbase[TObj(hmop).cid][TObj(hmop).id].maxhp;
      [*] = ;                  var hopct : Integer = 100;
      [*] = ;                  if (homax > 0) then
      [*] = ;                  hopct := Round((TObj(hmop).hp * 100) / homax);
      [*] = ;                  var hodone : Integer = 0;
      [*] = ;                  if (TObj(hmop).bbuilt) then
      [*] = ;                  hodone := 1;
      [*] = ;                  if (hou = gc_obj_usage_hardwall) or (hou = gc_obj_usage_weakwall) then
      [*] = ;                  begin
      [*] = ;                     hmowseg := hmowseg + 1;
      [*] = ;                     var hocx : Integer = floor(hox*cHmGrid/hmw);
      [*] = ;                     var hocy : Integer = floor(hoz*cHmGrid/hmh);
      [*] = ;                     if (hocx>=0) and (hocx<cHmGrid) and (hocy>=0) and (hocy<cHmGrid) then
      [*] = ;                     begin
      [*] = ;                        if (hou = gc_obj_usage_weakwall) then
      [*] = ;                        hmows[hocx][hocy] := hmows[hocx][hocy] + 1;
      [*] = ;                        if (hou = gc_obj_usage_hardwall) then
      [*] = ;                        hmowh[hocx][hocy] := hmowh[hocx][hocy] + 1;
      [*] = ;                        if (gObjProp[TObj(hmop).cid][TObj(hmop).id].bgate) then
      [*] = ;                        hmowg[hocx][hocy] := hmowg[hocx][hocy] + 1;
      [*] = ;                        if (hodone = 0) then
      [*] = ;                        hmowb[hocx][hocy] := hmowb[hocx][hocy] + 1;
      [*] = ;                        if (hopct < hmowm[hocx][hocy]) then
      [*] = ;                        hmowm[hocx][hocy] := hopct;
      [*] = ;                     end;
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     hmoball := hmoball + 1;
      [*] = ;                     if (hmobn < 60) then
      [*] = ;                     begin
      [*] = ;                        var honame : String = 'other';
      [*] = ;                        var hok2 : Integer;
      [*] = ;                        for hok2 := 0 to 17 do
      [*] = ;                        if (hbr[hok2] = gObjProp[TObj(hmop).cid][TObj(hmop).id].airole) then
      [*] = ;                        honame := hbn[hok2];
      [*] = ;                        if (hmobn > 0) then
      [*] = ;                        hmob := hmob + ';';
      [*] = ;                        hmob := hmob + honame + ',' + IntToStr(hox) + ',' + IntToStr(hoz) +
      [*] = ;                             ',' + IntToStr(hodone) + ',' + IntToStr(hopct);
      [*] = ;                        hmobn := hmobn + 1;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hmfn > 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'my_army_cx', hmfx div hmfn);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'my_army_cy', hmfy div hmfn);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'my_army_n',  hmfn);
      [*] = ;            end;
      [*] = ;            if (hmwn > 0) then
      [*] = ;            begin
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'wave_cx', hmwx div hmwn);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'wave_cy', hmwy div hmwn);
      [*] = ;               ParserSetIntValueByKeyByHandle(hsp, 'wave_n',  hmwn);
      [*] = ;            end;
      [*] = ;            var hmrow : String;
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               hmrow := '';
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  var hmv : Integer = hmbase[hmi][hmj];
      [*] = ;                  if (hmv = 1) then hmrow := hmrow + 'a';
      [*] = ;                  if (hmv = 2) then hmrow := hmrow + 'b';
      [*] = ;                  if (hmv = 3) then hmrow := hmrow + 'e';
      [*] = ;                  if (hmv = 4) then hmrow := hmrow + 'H';
      [*] = ;                  if (hmv = 0) then hmrow := hmrow + '.';
      [*] = ;               end;
      [*] = ;               ParserSetValueByKeyByHandle(hsp, 'brow'+IntToStr(hmj), hmrow);
      [*] = ;            end;
      [*] = ;            // COUNTS ABOVE NINE. Until 18.09 a cell showed at most '9', and a
      [*] = ;            // raid of sixty read as 'not less than 27' over three cells - the
      [*] = ;            // model could not tell a picket from an army at its own gate. One
      [*] = ;            // mark per cell stays (the grid is fixed width): 1-9 as digits,
      [*] = ;            // 10-35 as letters a-z, 36 and more as '+'. SubStr is 1-based and
      [*] = ;            // is what the native blocks use to pick a char out of a row.
      [*] = ;            var hmalpha : String = 'abcdefghijklmnopqrstuvwxyz';
      [*] = ;            // SECOND ALPHABET (26.09, asked by the mac): 36-61 as A-Z, 62 and
      [*] = ;            // more as '+'. Uppercase is unambiguous next to the lowercase a-z,
      [*] = ;            // the row stays 16 chars wide, and every reader of 0-35 keeps
      [*] = ;            // working - so the 213 runs already recorded stay comparable.
      [*] = ;            // This alone does NOT close the request: one char tops out at 61,
      [*] = ;            // and the battle that prompted it had 194 of ours in one cell.
      [*] = ;            // The exact numbers written after the grids do close it.
      [*] = ;            var hmbig : String = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               hmrow := '';
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  var hmf : Integer = hmforce[hmi][hmj];
      [*] = ;                  if (hmf = 0) then hmrow := hmrow + '.';
      [*] = ;                  if (hmf > 0) and (hmf <= 9) then hmrow := hmrow + IntToStr(hmf);
      [*] = ;                  if (hmf > 9) and (hmf <= 35) then hmrow := hmrow + SubStr(hmalpha, hmf-9, 1);
      [*] = ;                  if (hmf > 35) and (hmf <= 61) then hmrow := hmrow + SubStr(hmbig, hmf-35, 1);
      [*] = ;                  if (hmf > 61) then hmrow := hmrow + '+';
      [*] = ;               end;
      [*] = ;               ParserSetValueByKeyByHandle(hsp, 'frow'+IntToStr(hmj), hmrow);
      [*] = ;            end;
      [*] = ;            // OUR OWN army on its OWN grid, and the enemy grid above is left
      [*] = ;            // untouched ON PURPOSE. Merging both into one char was tried first
      [*] = ;            // and rejected: a contact cell would have had to hide the enemy
      [*] = ;            // count behind a single mark, and coss3_map.py reads frow digits
      [*] = ;            // to find who stands near us - a merged cell would have dropped a
      [*] = ;            // fighting enemy out of that analysis altogether. The extra grid
      [*] = ;            // costs about 300 characters a tick; a silent wrong reader costs more.
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               hmrow := '';
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  var hmo : Integer = hmown[hmi][hmj];
      [*] = ;                  if (hmo = 0) then hmrow := hmrow + '.';
      [*] = ;                  if (hmo > 0) and (hmo <= 9) then hmrow := hmrow + IntToStr(hmo);
      [*] = ;                  if (hmo > 9) and (hmo <= 35) then hmrow := hmrow + SubStr(hmalpha, hmo-9, 1);
      [*] = ;                  if (hmo > 35) and (hmo <= 61) then hmrow := hmrow + SubStr(hmbig, hmo-35, 1);
      [*] = ;                  if (hmo > 61) then hmrow := hmrow + '+';
      [*] = ;               end;
      [*] = ;               ParserSetValueByKeyByHandle(hsp, 'arow'+IntToStr(hmj), hmrow);
      [*] = ;            end;
      [*] = ;            // Enemy peasants on their own grid, same marks as frow/arow.
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               hmrow := '';
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  var hmq : Integer = hmpea[hmi][hmj];
      [*] = ;                  if (hmq = 0) then hmrow := hmrow + '.';
      [*] = ;                  if (hmq > 0) and (hmq <= 9) then hmrow := hmrow + IntToStr(hmq);
      [*] = ;                  if (hmq > 9) and (hmq <= 35) then hmrow := hmrow + SubStr(hmalpha, hmq-9, 1);
      [*] = ;                  if (hmq > 35) and (hmq <= 61) then hmrow := hmrow + SubStr(hmbig, hmq-35, 1);
      [*] = ;                  if (hmq > 61) then hmrow := hmrow + '+';
      [*] = ;               end;
      [*] = ;               ParserSetValueByKeyByHandle(hsp, 'prow'+IntToStr(hmj), hmrow);
      [*] = ;            end;
      [*] = ;            // Destinations of his moving soldiers, same marks as frow.
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               hmrow := '';
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  var hmd : Integer = hmdest[hmi][hmj];
      [*] = ;                  if (hmd = 0) then hmrow := hmrow + '.';
      [*] = ;                  if (hmd > 0) and (hmd <= 9) then hmrow := hmrow + IntToStr(hmd);
      [*] = ;                  if (hmd > 9) and (hmd <= 35) then hmrow := hmrow + SubStr(hmalpha, hmd-9, 1);
      [*] = ;                  if (hmd > 35) and (hmd <= 61) then hmrow := hmrow + SubStr(hmbig, hmd-35, 1);
      [*] = ;                  if (hmd > 61) then hmrow := hmrow + '+';
      [*] = ;               end;
      [*] = ;               ParserSetValueByKeyByHandle(hsp, 'drow'+IntToStr(hmj), hmrow);
      [*] = ;            end;
      [*] = ;            // EXACT NUMBERS FOR CONTACT CELLS, no ceiling at all. Why the grid is not
      [*] = ;            // enough: one mark per cell saturates. '+' used to mean 36 and more; with
      [*] = ;            // A-Z above it means 62 and more - and the battle that prompted this had
      [*] = ;            // 194 of ours against 36 of his in ONE cell, so both sides read as '+'
      [*] = ;            // and the exchange could not be explained by numbers at all.
      [*] = ;            // Only cells where OUR army stands together with his fighters or his
      [*] = ;            // peasants: those are the ones a fight can be measured in, and there are
      [*] = ;            // few of them, so the line stays short. Written as
      [*] = ;            // x,y,ours,his,peasants separated by ';'. 'none' when there are none:
      [*] = ;            // a missing key and a measured zero must not look the same (14.09).
      [*] = ;            hmcs := '';
      [*] = ;            hmcn := 0;
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  if (hmown[hmi][hmj] > 0) and (hmcn < 12) then
      [*] = ;                  begin
      [*] = ;                     if (hmforce[hmi][hmj] > 0) or (hmpea[hmi][hmj] > 0) then
      [*] = ;                     begin
      [*] = ;                        if (hmcn > 0) then
      [*] = ;                        hmcs := hmcs + ';';
      [*] = ;                        // DISTANCE BETWEEN THE TWO CROWDS inside this cell, in engine
      [*] = ;                        // units (a cell is 16 of them, so 0..22 along the diagonal).
      [*] = ;                        // -1 means one of the sides is not in the cell at all, so there
      [*] = ;                        // is no distance to speak of: a measured zero and a missing
      [*] = ;                        // side must not look the same. Sixth field on purpose - the
      [*] = ;                        // five before it keep their places and old readers survive.
      [*] = ;                        var hmdd : Integer = -1;
      [*] = ;                        if (hmown[hmi][hmj] > 0) and (hmforce[hmi][hmj] > 0) then
      [*] = ;                        begin
      [*] = ;                           var hmddx : Integer = (hmsox[hmi][hmj] div hmown[hmi][hmj]) - (hmsex[hmi][hmj] div hmforce[hmi][hmj]);
      [*] = ;                           var hmddz : Integer = (hmsoz[hmi][hmj] div hmown[hmi][hmj]) - (hmsez[hmi][hmj] div hmforce[hmi][hmj]);
      [*] = ;                           hmdd := Round(Sqrt(hmddx*hmddx + hmddz*hmddz));
      [*] = ;                        end;
      [*] = ;                        hmcs := hmcs + IntToStr(hmi) + ',' + IntToStr(hmj) + ',' +
      [*] = ;                             IntToStr(hmown[hmi][hmj]) + ',' + IntToStr(hmforce[hmi][hmj]) + ',' +
      [*] = ;                             IntToStr(hmpea[hmi][hmj]) + ',' + IntToStr(hmdd);
      [*] = ;                        hmcn := hmcn + 1;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hmcs = '') then
      [*] = ;            hmcs := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'cells', hmcs);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'cells_n', hmcn);
      [*] = ;            // HIS ARMY BY CELLS, WITH MAKE-UP AND ORDERS (29.09, P1). Written as
      [*] = ;            // x,y,n,pike,shoot,cav,nmove,tx,ty through ';', at most 24 cells,
      [*] = ;            // 'none' when his army is nowhere - a missing key and a measured zero
      [*] = ;            // must not look the same (14.09). tx,ty is the AVERAGE destination cell
      [*] = ;            // of the nmove men of that cell, -1,-1 when nmove is zero: there is no
      [*] = ;            // destination to average, and 0,0 is a real corner of the map.
      [*] = ;            // WHY THREE BANDS instead of sorting. The mac asked for the cells by
      [*] = ;            // descending n, and a sort of 256 cells every game second is not worth
      [*] = ;            // its cost; a plain scan order would cut the biggest cell if it came
      [*] = ;            // late in the scan. Three passes - ten and above, five to nine, the
      [*] = ;            // rest - cost 768 comparisons, cannot drop a crowd in favour of a
      [*] = ;            // picket, and are not a sort inside a band. ecells_all counts EVERY
      [*] = ;            // cell with his fighters, so a cut at 24 is said out loud.
      [*] = ;            hmes := '';
      [*] = ;            hmen := 0;
      [*] = ;            hmeall := 0;
      [*] = ;            for hmband := 0 to 2 do
      [*] = ;            begin
      [*] = ;               for hmj := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  for hmi := 0 to cHmGrid-1 do
      [*] = ;                  begin
      [*] = ;                     var hmev : Integer = hmforce[hmi][hmj];
      [*] = ;                     var hmeb : Integer = 2;
      [*] = ;                     if (hmev > 9) then hmeb := 0;
      [*] = ;                     if (hmev > 4) and (hmev < 10) then hmeb := 1;
      [*] = ;                     if (hmev > 0) and (hmeb = hmband) then
      [*] = ;                     begin
      [*] = ;                        hmeall := hmeall + 1;
      [*] = ;                        if (hmen < 24) then
      [*] = ;                        begin
      [*] = ;                           if (hmen > 0) then
      [*] = ;                           hmes := hmes + ';';
      [*] = ;                           var hmetc : Integer = -1;
      [*] = ;                           var hmetd : Integer = -1;
      [*] = ;                           if (hmemn[hmi][hmj] > 0) then
      [*] = ;                           begin
      [*] = ;                              hmetc := hmetx[hmi][hmj] div hmemn[hmi][hmj];
      [*] = ;                              hmetd := hmetz[hmi][hmj] div hmemn[hmi][hmj];
      [*] = ;                           end;
      [*] = ;                           hmes := hmes + IntToStr(hmi) + ',' + IntToStr(hmj) + ',' +
      [*] = ;                                IntToStr(hmev) + ',' + IntToStr(hmepk[hmi][hmj]) + ',' +
      [*] = ;                                IntToStr(hmesh[hmi][hmj]) + ',' + IntToStr(hmecv[hmi][hmj]) + ',' +
      [*] = ;                                IntToStr(hmemn[hmi][hmj]) + ',' +
      [*] = ;                                IntToStr(hmetc) + ',' + IntToStr(hmetd) + ',' +
      [*] = ;                                IntToStr(hme18[hmi][hmj]);
      [*] = ;                           hmen := hmen + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hmes = '') then
      [*] = ;            hmes := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'ecells', hmes);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ecells_n', hmen);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ecells_all', hmeall);
      [*] = ;            // OUR ARMY BY CELLS WITH MAKE-UP (29.09, P2): x,y,n,pike,shoot,cav.
      [*] = ;            // No orders here - my_army_n and wave_n already split ours into the
      [*] = ;            // fist at home and the wave in the field, and an unproven second way
      [*] = ;            // of saying the same thing would only let the two disagree.
      [*] = ;            hmos := '';
      [*] = ;            hmon := 0;
      [*] = ;            hmoall := 0;
      [*] = ;            for hmband := 0 to 2 do
      [*] = ;            begin
      [*] = ;               for hmj := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  for hmi := 0 to cHmGrid-1 do
      [*] = ;                  begin
      [*] = ;                     var hmov : Integer = hmown[hmi][hmj];
      [*] = ;                     var hmob : Integer = 2;
      [*] = ;                     if (hmov > 9) then hmob := 0;
      [*] = ;                     if (hmov > 4) and (hmov < 10) then hmob := 1;
      [*] = ;                     if (hmov > 0) and (hmob = hmband) then
      [*] = ;                     begin
      [*] = ;                        hmoall := hmoall + 1;
      [*] = ;                        if (hmon < 24) then
      [*] = ;                        begin
      [*] = ;                           if (hmon > 0) then
      [*] = ;                           hmos := hmos + ';';
      [*] = ;                           hmos := hmos + IntToStr(hmi) + ',' + IntToStr(hmj) + ',' +
      [*] = ;                                IntToStr(hmov) + ',' + IntToStr(hmopk[hmi][hmj]) + ',' +
      [*] = ;                                IntToStr(hmosh[hmi][hmj]) + ',' + IntToStr(hmocv[hmi][hmj]);
      [*] = ;                           hmon := hmon + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hmos = '') then
      [*] = ;            hmos := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'ocells', hmos);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ocells_n', hmon);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ocells_all', hmoall);
      [*] = ;            // GROUPS WITH NAMES (4.10, par.78 of the mac): our armies with numbers,
      [*] = ;            // made by the command block (field `group` of an order) and remembered
      [*] = ;            // in the parser br_hgrp. Row: id,n,pike,shooters,horse,cx,cy,mode,tx,ty.
      [*] = ;            // WHY FROM A PARSER AND NOT FROM THE ENGINE: the script API has no way
      [*] = ;            // to walk a player's groups or read a group's members - only
      [*] = ;            // _misc_GetOrCreateGroupByName, GroupAdd/Clear and _group_Initialize.
      [*] = ;            // And a unit cannot be marked either: the field that would fit,
      [*] = ;            // scenariogroupid, is read on death (units/unit.inc/ondeath.inc:23)
      [*] = ;            // and sends the engine into gScenario, which a skirmish does not have.
      [*] = ;            // ALL COUNTERS ARE DECLARED HERE, before the loops: a number declared
      [*] = ;            // inside a nested begin does not accumulate (six army counters, 17.09).
      [*] = ;            var hggp : Integer = ParserSelectByKey('br_hgrp');
      [*] = ;            var hgstr : String = '';
      [*] = ;            var hgrows : Integer = 0;
      [*] = ;            var hgid : Integer;
      [*] = ;            var hgk : Integer;
      [*] = ;            var hgcnt : Integer;
      [*] = ;            var hgliv : Integer;
      [*] = ;            var hgpk : Integer;
      [*] = ;            var hgsh : Integer;
      [*] = ;            var hgcv : Integer;
      [*] = ;            var hgsx : Integer;
      [*] = ;            var hgsz : Integer;
      [*] = ;            var hgtx : Integer;
      [*] = ;            var hgty : Integer;
      [*] = ;            var hgmode : Integer;
      [*] = ;            // Cells and live counts BY GROUP NUMBER, for the merge pass below.
      [*] = ;            // Arrays, not scalars: an array survives a nested begin by reference,
      [*] = ;            // a number does not (six army counters, 17.09).
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 9);
      [*] = ;            var hgcell : array [0..16] of Integer;
      [*] = ;            var hgcelly : array [0..16] of Integer;
      [*] = ;            var hglive : array [0..16] of Integer;
      [*] = ;            var hgto : Integer;
      [*] = ;            for hgid := 0 to 16 do
      [*] = ;            begin
      [*] = ;               hgcell[hgid] := -1;
      [*] = ;               hgcelly[hgid] := -1;
      [*] = ;               hglive[hgid] := 0;
      [*] = ;            end;
      [*] = ;            // NEW GAME, OLD ROLLS (29.10, D26/D27): br_hgrp outlives the match - the parser is not cleared on NEW, so a
      [*] = ;            // wave of the previous game sat in g1 with handles the engine had already given to new objects (D26 'group 1' of
      [*] = ;            // 16 at 4:07 without any order, D27 three cleanings of 4/8/25 with nobody ordered). In the first seconds the rolls are zeroed.
      [*] = ;            if (hggp <> 0) and (hsnow < 15) then
      [*] = ;            for hgid := 1 to 16 do
      [*] = ;            ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_n', 0);
      [*] = ;            if (hggp <> 0) then
      [*] = ;            for hgid := 1 to 16 do
      [*] = ;            begin
      [*] = ;               hgcnt := ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_n');
      [*] = ;               if (hgcnt > 0) then
      [*] = ;               begin
      [*] = ;                  hgliv := 0;
      [*] = ;                  hgpk := 0;
      [*] = ;                  hgsh := 0;
      [*] = ;                  hgcv := 0;
      [*] = ;                  hgsx := 0;
      [*] = ;                  hgsz := 0;
      [*] = ;                  hgtx := -1;
      [*] = ;                  hgty := -1;
      [*] = ;                  hgmode := ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_m');
      [*] = ;                  hgw := 0;
      [*] = ;                  hgdrop := 0;
      [*] = ;                  hgforeign := 0;
      [*] = ;                  hgownpl := -1;
      [*] = ;                  for hgk := 0 to hgcnt-1 do
      [*] = ;                  begin
      [*] = ;                     var hgh : Integer = ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_h' + IntToStr(hgk));
      [*] = ;                     hgkeep := False;
      [*] = ;                     if (hgh <> 0) then
      [*] = ;                     begin
      [*] = ;                        var hgp : Pointer = _unit_GetTObj(hgh);
      [*] = ;                        if (hgp<>nil) then
      [*] = ;                        if (not TObj(hgp).bdead) then
      [*] = ;                        begin
      [*] = ;                           // OWNER IS DIAGNOSTIC ONLY (30.10, Poland game): the index test dropped 77 of 77 LIVE men of a fresh wave on the
      [*] = ;                           // human-slot bot (plind 1), while in containers (plind 0) it passed; the roll then had nobody and the python lost the
      [*] = ;                           // wave. Dead and nil handles are still dropped - that is the freeze guard; a foreign owner is counted and logged.
      [*] = ;                           if (hgownpl < 0) then
      [*] = ;                           if (GetPlayerIndexByHandle(GetGameObjectPlayerHandleByHandle(hgh)) <> plind) then
      [*] = ;                           hgownpl := GetPlayerIndexByHandle(GetGameObjectPlayerHandleByHandle(hgh));
      [*] = ;                           if (GetPlayerIndexByHandle(GetGameObjectPlayerHandleByHandle(hgh)) <> plind) then
      [*] = ;                           hgforeign := hgforeign + 1;
      [*] = ;                           hgkeep := True;
      [*] = ;                           var hgu : Integer = gObjProp[TObj(hgp).cid][TObj(hgp).id].usage;
      [*] = ;                           hgliv := hgliv + 1;
      [*] = ;                           hgsx := hgsx + Round(GetGameObjectPositionXByHandle(hgh)+hmhw);
      [*] = ;                           hgsz := hgsz + Round(GetGameObjectPositionZByHandle(hgh)+hmhh);
      [*] = ;                           // The same three marks as mil_inf/mil_shooters/mil_cav,
      [*] = ;                           // so the columns sum to n exactly as they do in ocells.
      [*] = ;                           if (hgu = gc_obj_usage_lightinfantry) or (hgu = gc_obj_usage_weak) or
      [*] = ;                              (hgu = gc_obj_usage_grenadier) then
      [*] = ;                           hgpk := hgpk + 1;
      [*] = ;                           if (hgu = gc_obj_usage_shooter) or (hgu = gc_obj_usage_archer) then
      [*] = ;                           hgsh := hgsh + 1;
      [*] = ;                           if (hgu = gc_obj_usage_fasthorse) or (hgu = gc_obj_usage_hardhorse) or
      [*] = ;                              (hgu = gc_obj_usage_horseshooter) then
      [*] = ;                           hgcv := hgcv + 1;
      [*] = ;                           // WHERE THE GROUP IS GOING: the first live man with an order
      [*] = ;                           // speaks for the group - they walk under one order. Same
      [*] = ;                           // reading as the enemy cells use (orders[0].info).
      [*] = ;                           if (hgtx < 0) then
      [*] = ;                           if (TObj(hgp).orders[0].itype <> gc_obj_order_type_none) then
      [*] = ;                           begin
      [*] = ;                              var hgox : Float = TObj(hgp).orders[0].info.x;
      [*] = ;                              var hgoy : Float = TObj(hgp).orders[0].info.y;
      [*] = ;                              if (TObj(hgp).orders[0].itype = gc_obj_order_type_attackobj) then
      [*] = ;                              if (TObj(hgp).orders[0].info.trg <> 0) then
      [*] = ;                              if (_unit_GetTObj(TObj(hgp).orders[0].info.trg) <> nil) then
      [*] = ;                              begin
      [*] = ;                                 hgox := GetGameObjectPositionXByHandle(TObj(hgp).orders[0].info.trg);
      [*] = ;                                 hgoy := GetGameObjectPositionZByHandle(TObj(hgp).orders[0].info.trg);
      [*] = ;                              end;
      [*] = ;                              if (hgox > -999999) then
      [*] = ;                              begin
      [*] = ;                                 hgtx := floor((hgox+hmhw)*cHmGrid/hmw);
      [*] = ;                                 hgty := floor((hgoy+hmhh)*cHmGrid/hmh);
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (hgkeep) then
      [*] = ;                     begin
      [*] = ;                        if (hgw <> hgk) then
      [*] = ;                        ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_h' + IntToStr(hgw), hgh);
      [*] = ;                        hgw := hgw + 1;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     hgdrop := hgdrop + 1;
      [*] = ;                  end;
      [*] = ;                  // ROLL CLEANING (29.10, D26 freeze named by the stage probe: stage 9, this loop).
      [*] = ;                  // Handles of men who died are kept in br_hgrp forever, and the engine REUSES a
      [*] = ;                  // freed handle for a new object: in D26 group 1 had 1 man alive at 13:07 and 5 at
      [*] = ;                  // 13:37 without any order - strangers under our old handles. Reading them is
      [*] = ;                  // what died here. A dead or foreign handle is dropped from the roll the second it
      [*] = ;                  // is seen (the body still exists then, so the handle is still valid), and the roll
      [*] = ;                  // is packed, so neither this block nor the command block touches it again.
      [*] = ;                  if (hgw < hgcnt) then
      [*] = ;                  begin
      [*] = ;                     for hgk := hgw to hgcnt-1 do
      [*] = ;                     ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_h' + IntToStr(hgk), 0);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_n', hgw);
      [*] = ;                     Log('bridge-human: GROUP ' + IntToStr(hgid) + ' roll cleaned at ' + IntToStr(Round(hsnow)) + ' s: ' + IntToStr(hgdrop) + ' of ' + IntToStr(hgcnt) +
      [*] = ;                          ' dead handles dropped, ' + IntToStr(hgw) + ' left, foreign owner kept ' + IntToStr(hgforeign) + ' (pl ' + IntToStr(hgownpl) + ' vs ' + IntToStr(plind) + ')');
      [*] = ;                  end;
      [*] = ;                  // A group with nobody alive is not written at all: the model must
      [*] = ;                  // not order a group that no longer exists.
      [*] = ;                  if (hgliv > 0) then
      [*] = ;                  begin
      [*] = ;                     if (hgrows > 0) then
      [*] = ;                     hgstr := hgstr + ';';
      [*] = ;                     hgstr := hgstr + IntToStr(hgid) + ',' + IntToStr(hgliv) + ',' +
      [*] = ;                          IntToStr(hgpk) + ',' + IntToStr(hgsh) + ',' + IntToStr(hgcv) + ',' +
      [*] = ;                          IntToStr(floor((hgsx div hgliv)*cHmGrid/hmw)) + ',' +
      [*] = ;                          IntToStr(floor((hgsz div hgliv)*cHmGrid/hmh)) + ',' +
      [*] = ;                          IntToStr(hgmode) + ',' + IntToStr(hgtx) + ',' + IntToStr(hgty);
      [*] = ;                     hgcell[hgid] := floor((hgsx div hgliv)*cHmGrid/hmw);
      [*] = ;                     hgcelly[hgid] := floor((hgsz div hgliv)*cHmGrid/hmh);
      [*] = ;                     hglive[hgid] := hgliv;
      [*] = ;                     hgrows := hgrows + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hgstr = '') then
      [*] = ;            hgstr := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'groups', hgstr);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'groups_n', hgrows);
      [*] = ;            ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 91);
      [*] = ;            // MERGE ON ARRIVAL (4.10, par.78). A group told to walk to another one
      [*] = ;            // carries g<A>_to = B. Arrived means THE SAME CELL - the same measure
      [*] = ;            // ocells and the whole post-mortem use, and the only one visible in the
      [*] = ;            // state. Then A's men are appended to B's roll and A is emptied: a group
      [*] = ;            // with nobody alive is not written at all, so A disappears by itself.
      [*] = ;            // Done here and not in the command block because only this one runs
      [*] = ;            // every tick, and arrival is not an event - it is a condition.
      [*] = ;            if (hggp <> 0) then
      [*] = ;            for hgid := 1 to 16 do
      [*] = ;            begin
      [*] = ;               hgto := ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_to');
      [*] = ;               if (hgto > 0) and (hgto <= 16) then
      [*] = ;               if (hglive[hgid] > 0) and (hglive[hgto] > 0) then
      [*] = ;               if (hgcell[hgid] = hgcell[hgto]) and (hgcelly[hgid] = hgcelly[hgto]) then
      [*] = ;               begin
      [*] = ;                  hgcnt := ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_n');
      [*] = ;                  var hgbn : Integer = ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgto) + '_n');
      [*] = ;                  for hgk := 0 to hgcnt-1 do
      [*] = ;                  begin
      [*] = ;                     var hgmh : Integer = ParserGetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_h' + IntToStr(hgk));
      [*] = ;                     if (hgmh <> 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgto) + '_h' + IntToStr(hgbn), hgmh);
      [*] = ;                        hgbn := hgbn + 1;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgto) + '_n', hgbn);
      [*] = ;                  ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_n', 0);
      [*] = ;                  ParserSetIntValueByKeyByHandle(hggp, 'g' + IntToStr(hgid) + '_to', 0);
      [*] = ;                  Log('bridge-human: GROUP ' + IntToStr(hgid) + ' merged into ' +
      [*] = ;                      IntToStr(hgto) + ', now ' + IntToStr(hgbn) + ' men');
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 92);
      [*] = ;            // BUILDINGS OF BOTH SIDES (29.09, P6): 'type,x,z,done,hp%' through ';',
      [*] = ;            // at most 60, with *_all saying how many there were in all. Coordinates
      [*] = ;            // are ENGINE UNITS SHIFTED to the grid frame (0..map_w), the same frame
      [*] = ;            // the cells use: cell = floor(x*16/map_w). Raw engine coordinates are
      [*] = ;            // centred on zero and would need the map size to be read twice.
      [*] = ;            if (hmeb = '') then
      [*] = ;            hmeb := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'ebuild', hmeb);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ebuild_n', hmebn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ebuild_all', hmeball);
      [*] = ;            if (hmob = '') then
      [*] = ;            hmob := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'obuild', hmob);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'obuild_n', hmobn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'obuild_all', hmoball);
      [*] = ;            // WALLS BY CELLS (29.09, P7): 'x,y,weak,hard,gates,building,hp%min'.
      [*] = ;            // Walls are kept APART from the building list on purpose: a palisade of
      [*] = ;            // eighty segments would fill the list of sixty and push out the barracks
      [*] = ;            // it exists for. hp%min is the WEAKEST segment of the cell - that is where
      [*] = ;            // a wall gets broken, and an average would hide it.
      [*] = ;            var hmwst : String = '';
      [*] = ;            var hmwsn : Integer = 0;
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  if (hmews[hmi][hmj] + hmewh[hmi][hmj] > 0) then
      [*] = ;                  begin
      [*] = ;                     if (hmwsn > 0) then
      [*] = ;                     hmwst := hmwst + ';';
      [*] = ;                     hmwst := hmwst + IntToStr(hmi) + ',' + IntToStr(hmj) + ',' +
      [*] = ;                          IntToStr(hmews[hmi][hmj]) + ',' + IntToStr(hmewh[hmi][hmj]) + ',' +
      [*] = ;                          IntToStr(hmewg[hmi][hmj]) + ',' + IntToStr(hmewb[hmi][hmj]) + ',' +
      [*] = ;                          IntToStr(hmewm[hmi][hmj]);
      [*] = ;                     hmwsn := hmwsn + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hmwst = '') then
      [*] = ;            hmwst := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'ewalls', hmwst);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ewalls_n', hmwsn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'ewalls_seg', hmewseg);
      [*] = ;            hmwst := '';
      [*] = ;            hmwsn := 0;
      [*] = ;            for hmj := 0 to cHmGrid-1 do
      [*] = ;            begin
      [*] = ;               for hmi := 0 to cHmGrid-1 do
      [*] = ;               begin
      [*] = ;                  if (hmows[hmi][hmj] + hmowh[hmi][hmj] > 0) then
      [*] = ;                  begin
      [*] = ;                     if (hmwsn > 0) then
      [*] = ;                     hmwst := hmwst + ';';
      [*] = ;                     hmwst := hmwst + IntToStr(hmi) + ',' + IntToStr(hmj) + ',' +
      [*] = ;                          IntToStr(hmows[hmi][hmj]) + ',' + IntToStr(hmowh[hmi][hmj]) + ',' +
      [*] = ;                          IntToStr(hmowg[hmi][hmj]) + ',' + IntToStr(hmowb[hmi][hmj]) + ',' +
      [*] = ;                          IntToStr(hmowm[hmi][hmj]);
      [*] = ;                     hmwsn := hmwsn + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hmwst = '') then
      [*] = ;            hmwst := 'none';
      [*] = ;            ParserSetValueByKeyByHandle(hsp, 'owalls', hmwst);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'owalls_n', hmwsn);
      [*] = ;            ParserSetIntValueByKeyByHandle(hsp, 'owalls_seg', hmowseg);
      [*] = ;            ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 93);
      [*] = ;         end;
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 94);
      [*] = ;         var hsupg : String;
      [*] = ;         // Which upgrades are ALREADY TAKEN and which are being paid for right now.
      [*] = ;         // The engine keeps both in gPlayer[pl].upgstate[cid][i] - the same pair the
      [*] = ;         // native AI asks about in _ai_IsUpgradeInProgressOrDone
      [*] = ;         // (progresseconomicai.inc:1429). Calling that function from here is not
      [*] = ;         // allowed - it lives in another script state - so we read the fields.
      [*] = ;         // Until 18.09 this was ONLY OUR OWN (player, 16.09: a human does not see
      [*] = ;         // the enemy upgrades). The rule is lifted; theirs go out as p<n>_upg_done.
      [*] = ;         var hsupgd, hsupgp : String;
      [*] = ;         var hsui : Integer;
      [*] = ;         for hsui := 0 to gc_country_maxupgradecount-1 do
      [*] = ;         begin
      [*] = ;            var hsus : String = gCountry[hscid].upgrade[hsui].id;
      [*] = ;            // 'null' is the engine's empty upgrade (_country_AddUpgrade(country, 'null', ...), country.script); cut to
      [*] = ;            // 'l' it went out as a free upgrade 'l=f0g0i0' (31.10, live snapshot). Skipped since hstate 2669.
      [*] = ;            var hsunull : Boolean = (hsus = 'null');
      [*] = ;            if (not hsunull) then
      [*] = ;            if (StrLength(hsus) > 3) then
      [*] = ;            begin
      [*] = ;               var hsun : String = SubStr(hsus, 4, StrLength(hsus)-3);
      [*] = ;               if (StrLength(hsupg) > 0) then
      [*] = ;               hsupg := hsupg + ',';
      [*] = ;               hsupg := hsupg + hsun;
      [*] = ;               // PRICE for the MILITARY upgrades only (a name with three dots, like
      [*] = ;               // bar.pikeman.1.4). Taken from the nation table the same way the refusal
      [*] = ;               // in block_hcmd reads it. Without the price the bridge cannot weigh a
      [*] = ;               // step against its cost: 19.09 the model climbed to the fifth step of
      [*] = ;               // attack at 16030 food and came out with a quarter less army. Only the
      [*] = ;               // military ones carry a price here - the rest would bloat the line, and
      [*] = ;               // the python side splits on '=' and keeps the name (llm_policy:5500).
      [*] = ;               var hsudots, hsudi : Integer;
      [*] = ;               hsudots := 0;
      [*] = ;               for hsudi := 1 to StrLength(hsun) do
      [*] = ;               if (SubStr(hsun, hsudi, 1) = '.') then
      [*] = ;               hsudots := hsudots + 1;
      [*] = ;               // ACADEMY TOO, since 20.09. Its names carry ONE dot
      [*] = ;               // ('aca.12') and used to fall out of this test, so the
      [*] = ;               // model saw an academy upgrade without a price - while
      [*] = ;               // aca.12..15 give +10..+25 per cent of BULLET damage and
      [*] = ;               // aca.31/33 cut its reload by 30 per cent each.
      [*] = ;               var hsupac : Boolean = (StrLength(hsun) > 4) and (SubStr(hsun, 1, 4) = 'aca.');
      [*] = ;               // LIST ITEM 4 (30.10 night): the price goes with EVERY upgrade, not only military (3 dots) and
      [*] = ;               // academic ones - bla.*, mil.*, sto.*, mil18 came without a price, and python could not weigh them
      [*] = ;               // (29.10: the bot bought aca.13 for 4000 while bla.1 had no number). hsudots/hsupac are kept for the record.
      [*] = ;               if (hsudots >= 0) then
      [*] = ;               begin
      [*] = ;                  var hsupf : Integer = gCountry[hscid].upgrade[hsui].price[gc_resource_type_food];
      [*] = ;                  var hsupg2 : Integer = gCountry[hscid].upgrade[hsui].price[gc_resource_type_gold];
      [*] = ;                  var hsupi : Integer = gCountry[hscid].upgrade[hsui].price[gc_resource_type_iron];
      [*] = ;                  hsupg := hsupg + '=f' + IntToStr(hsupf) + 'g' + IntToStr(hsupg2) + 'i' + IntToStr(hsupi);
      [*] = ;                  // Wood, stone and coal ONLY when non-zero: military
      [*] = ;                  // upgrades never cost them, and three zeroes on every
      [*] = ;                  // name would bloat the line for nothing. Academy does
      [*] = ;                  // cost them - aca.31 wants 6000 stone on top.
      [*] = ;                  var hsupw : Integer = gCountry[hscid].upgrade[hsui].price[gc_resource_type_wood];
      [*] = ;                  var hsups : Integer = gCountry[hscid].upgrade[hsui].price[gc_resource_type_stone];
      [*] = ;                  var hsupc : Integer = gCountry[hscid].upgrade[hsui].price[gc_resource_type_coal];
      [*] = ;                  if (hsupw > 0) then
      [*] = ;                  hsupg := hsupg + 'w' + IntToStr(hsupw);
      [*] = ;                  if (hsups > 0) then
      [*] = ;                  hsupg := hsupg + 's' + IntToStr(hsups);
      [*] = ;                  if (hsupc > 0) then
      [*] = ;                  hsupg := hsupg + 'c' + IntToStr(hsupc);
      [*] = ;               end;
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
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 10);
      [*] = ;         var hsvic : String = 'none';
      [*] = ;         if (gPlayer[plind].victorystate = gc_player_victorystate_win) then
      [*] = ;         hsvic := 'win'
      [*] = ;         else
      [*] = ;         if (gPlayer[plind].victorystate = gc_player_victorystate_lose) then
      [*] = ;         hsvic := 'lose';
      [*] = ;         ParserSetValueByKeyByHandle(hsp, 'victory', hsvic);
      [*] = ;         ParserSaveToFileByHandle(hsp, '@@OUT@@coss3_eco_P' + IntToStr(plind) + '.dat');
      [*] = ;         ParserSetIntValueByKeyByHandle(hshb, 'stage' + IntToStr(plind), 11);
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE HUMAN STATE ===