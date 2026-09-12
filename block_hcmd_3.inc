      [*] = ;   // === BRIDGE HUMAN COMMANDS: the bot plays the human side itself ===
      [*] = ;   // BISECTION STEP: everything except ATTACK
      [*] = ;   // Same command file as the AI-side bridge (coss3_cmd_P<n>.dat), same numbers,
      [*] = ;   // so everything above the bridge - model, prompts, logs, replay - is unchanged.
      [*] = ;   // What changes is who executes: instead of dropping an idea into the native AI
      [*] = ;   // queue we call the engine directly, exactly as the game does for a human.
      [*] = ;   if (gPlayer[plind].bexists) and (not gPlayer[plind].bai) and
      [*] = ;      (not _net_IsClient) and (not _net_IsReplay) and
      [*] = ;      (gMap.gamestage = gc_map_gamestage_started) then
      [*] = ;   begin
      [*] = ;      // The game writes no log at all unless asked: cossacks.ini ships with
      [*] = ;      // LogFileEnabled=false, and every bridge: line we ever wrote went nowhere.
      [*] = ;      // Turn it on from here, once per session - no ini editing, reversible, and
      [*] = ;      // it costs nothing but a boolean. Without this there is no bot action log.
      [*] = ;      // Why a command failed must reach the MODEL, not just the log. Left in the
      [*] = ;      // dark it invents a reason: on the mock it decided within a minute that
      [*] = ;      // buildings cost food. The state block picks this up next tick.
      [*] = ;      var hfl : Integer = ParserSelectByKey('br_hfail');
      [*] = ;      if (hfl = 0) then
      [*] = ;      hfl := ParserCreate('br_hfail');
      [*] = ;      var hlg : Integer = ParserSelectByKey('br_hlog');
      [*] = ;      if (hlg = 0) then
      [*] = ;      begin
      [*] = ;         hlg := ParserCreate('br_hlog');
      [*] = ;         if (not GetLogFileEnabled) then
      [*] = ;         SetLogFileEnabled(True);
      [*] = ;         Log('bridge-human: log enabled, human-slot bot is live for P' + IntToStr(plind));
      [*] = ;      end;
      [*] = ;      var hcpath : String = '@@OUT@@coss3_cmd_P' + IntToStr(plind) + '.dat';
      [*] = ;      if IsFileExists(hcpath) then
      [*] = ;      begin
      [*] = ;         var hch : Integer = ParserSelectByKey('br_hcmd');
      [*] = ;         if (hch = 0) then
      [*] = ;         hch := ParserCreate('br_hcmd');
      [*] = ;         ParserClearByHandle(hch);
      [*] = ;         var hcok : Boolean = ParserLoadFromFileByHandle(hch, hcpath);
      [*] = ;         DeleteFileStream(hcpath);
      [*] = ;         if (hcok) then
      [*] = ;         begin
      [*] = ;            // A new batch of commands - the old failure reason has been read.
      [*] = ;            // Cleared HERE, not on state write: the state is written every
      [*] = ;            // second and the model reads it every fifteen.
      [*] = ;            ParserSetValueByKeyByHandle(hfl, 'why', '');
      [*] = ;            var hccid : Integer = gPlayer[plind].cid;
      [*] = ;            var hcph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var hccount : Integer = ParserGetIntValueByKeyByHandle(hch, 'count');
      [*] = ;            var hcn : Integer;
      [*] = ;            // Our own centre: needed as the anchor for placement and for picking
      [*] = ;            // the nearest resources. Found by scan - a human has no aidata.centerx.
      [*] = ;            var hcx, hcz : Float;
      [*] = ;            var hcbase : Integer = 0;
      [*] = ;            var hck : Integer;
      [*] = ;            var hcobjn : Integer = GetPlayerGameObjectsCountByHandle(hcph);
      [*] = ;            for hck := 0 to hcobjn-1 do
      [*] = ;            begin
      [*] = ;               var hcgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;               var hcpo : Pointer = _unit_GetTObj(hcgo);
      [*] = ;               if (hcpo<>nil) and (hcbase = 0) then
      [*] = ;               if (gObjProp[TObj(hcpo).cid][TObj(hcpo).id].airole = gc_ai_unit_center) then
      [*] = ;               begin
      [*] = ;                  hcbase := hcgo;
      [*] = ;                  hcx := GetGameObjectPositionXByHandle(hcgo);
      [*] = ;                  hcz := GetGameObjectPositionZByHandle(hcgo);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (hcbase = 0) then
      [*] = ;            begin
      [*] = ;               // No town centre yet: anchor on any object we own, usually a peasant.
      [*] = ;               if (hcobjn > 0) then
      [*] = ;               begin
      [*] = ;                  var hcany : Integer = GetGameObjectHandleByIndex(0, hcph);
      [*] = ;                  hcx := GetGameObjectPositionXByHandle(hcany);
      [*] = ;                  hcz := GetGameObjectPositionZByHandle(hcany);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // BUILDERS may arrive after BUILD in the same file, so read the cap
      [*] = ;            // first: a pre-pass costs nothing and removes an ordering trap.
      [*] = ;            var hccap : Integer = 3;
      [*] = ;            for hcn := 0 to hccount-1 do
      [*] = ;            if (ParserGetValueByKeyByHandle(hch, IntToStr(hcn) + '_cmd') = 'BUILDERS') then
      [*] = ;            begin
      [*] = ;               var hcv : Integer = ParserGetIntValueByKeyByHandle(hch, IntToStr(hcn) + '_a1');
      [*] = ;               if (hcv > 0) then
      [*] = ;               hccap := hcv;
      [*] = ;            end;
      [*] = ;            for hcn := 0 to hccount-1 do
      [*] = ;            begin
      [*] = ;               var hckey : String = IntToStr(hcn) + '_';
      [*] = ;               var hccmd : String = ParserGetValueByKeyByHandle(hch, hckey + 'cmd');
      [*] = ;               var hca1 : Integer = ParserGetIntValueByKeyByHandle(hch, hckey + 'a1');
      [*] = ;               var hca2 : Integer = ParserGetIntValueByKeyByHandle(hch, hckey + 'a2');
      [*] = ;               // --- role -> object id. gObjProp carries airole for every object,
      [*] = ;               // so a human resolves roles exactly like the AI, without aidata. ---
      [*] = ;               var hcid : Integer = -1;
      [*] = ;               var hcj : Integer;
      [*] = ;               if (hca1 > 0) then
      [*] = ;               for hcj := 0 to gc_country_maxmembers-1 do
      [*] = ;               if (hcid < 0) and (gObjProp[hccid][hcj].airole = hca1) then
      [*] = ;               hcid := hcj;
      [*] = ;               // A role this nation has no object for used to vanish here without
      [*] = ;               // a trace, and from the Python side that is indistinguishable from
      [*] = ;               // 'not enough resources'. Say it out loud instead.
      [*] = ;               if (hcid < 0) and (hca1 > 0) then
      [*] = ;               if (hccmd = 'BUILD') or (hccmd = 'TRAIN') then
      [*] = ;               begin
      [*] = ;                  ParserSetValueByKeyByHandle(hfl, 'why', hccmd + ' role' +
      [*] = ;                       IntToStr(hca1) + ': this nation has no such object');
      [*] = ;                  Log('bridge-human: ' + hccmd + ' role' + IntToStr(hca1) +
      [*] = ;                      ' - no such object for this nation');
      [*] = ;               end;
      [*] = ;               if (hccmd = 'BUILD') and (hcid >= 0) then
      [*] = ;               begin
      [*] = ;                  var hcsid : String = gCountry[hccid].members[hcid];
      [*] = ;                  // Do we already have enough of these? BUILD is declarative.
      [*] = ;                  var hchave : Integer;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hpo : Pointer = _unit_GetTObj(hgo);
      [*] = ;                     if (hpo<>nil) and (TObj(hpo).cid = hccid) and (TObj(hpo).id = hcid) then
      [*] = ;                     hchave := hchave + 1;
      [*] = ;                  end;
      [*] = ;                  if (hchave < hca2) and (_unit_CanApplyCostByID(hccid, hcid, plind)) then
      [*] = ;                  begin
      [*] = ;                     // Pick a spot: rings around the base, first valid one wins.
      [*] = ;                     // The dummy is the game's own placement preview object; it is
      [*] = ;                     // destroyed right after the check and never costs anything.
      [*] = ;                     var hcmisc : Integer = GetPlayerHandleByIndex(gc_playerind_misc);
      [*] = ;                     var hcrad : Float = 4.0;
      [*] = ;                     var hcang : Integer;
      [*] = ;                     var hcfx, hcfz : Float;
      [*] = ;                     var hcfound : Boolean = False;
      [*] = ;                     while (hcrad < 26.0) and (not hcfound) do
      [*] = ;                     begin
      [*] = ;                        for hcang := 0 to 11 do
      [*] = ;                        if (not hcfound) then
      [*] = ;                        begin
      [*] = ;                           var hctx : Float = hcx + hcrad * Cos(hcang * 0.5236);
      [*] = ;                           var hctz : Float = hcz + hcrad * Sin(hcang * 0.5236);
      [*] = ;                           var hcdum : Integer = _player_CreateConstructionDummyBySID(hcmisc, hccid, hcsid, hctx, hctz);
      [*] = ;                           if (hcdum <> 0) then
      [*] = ;                           begin
      [*] = ;                              var hcusage : Integer = gObjProp[hccid][hcid].usage;
      [*] = ;                              var hcvalid : Boolean;
      [*] = ;                              if (hcusage = gc_obj_usage_mine) then
      [*] = ;                              hcvalid := _misc_CanPlaceBuilding(hcdum, plind, hcusage, hctx, hctz, 0, 0.26, 0, -1, True)
      [*] = ;                              else
      [*] = ;                              hcvalid := _misc_CanPlaceBuilding(hcdum, plind, hcusage, hctx, hctz,
      [*] = ;                                   gc_path_mincoldist, 0.26, 0.5, gc_path_minemincoldist, True);
      [*] = ;                              GameObjectDestroyByHandle(hcdum);
      [*] = ;                              if (hcvalid) then
      [*] = ;                              begin
      [*] = ;                                 hcfound := True;
      [*] = ;                                 hcfx := hctx;
      [*] = ;                                 hcfz := hctz;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        hcrad := hcrad + 2.0;
      [*] = ;                     end;
      [*] = ;                     if (hcfound) then
      [*] = ;                     begin
      [*] = ;                        // Builders: idle peasants first, up to the cap the model set
      [*] = ;                        // (BUILDERS command, default 3). The engine would call every
      [*] = ;                        // peasant that fits around the site and strip the mines bare.
      [*] = ;                        gIntegerList.Clear;
      [*] = ;                        // IDLE peasants first, and only then the busy ones. The
      [*] = ;                        // engine does the opposite - it grabs whoever fits around
      [*] = ;                        // the site and strips the mines bare. We already paid for
      [*] = ;                        // that lesson on the AI side; do not repeat it here.
      [*] = ;                        var hwpass : Integer;
      [*] = ;                        // Second pass runs ONLY if there were no idle peasants at
      [*] = ;                        // all - otherwise the same man would be added twice.
      [*] = ;                        for hwpass := 0 to 1 do
      [*] = ;                        if (hwpass = 0) or (gIntegerList.GetCount = 0) then
      [*] = ;                        for hck := 0 to hcobjn-1 do
      [*] = ;                        if (gIntegerList.GetCount < hccap) then
      [*] = ;                        begin
      [*] = ;                           var hwgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hwpo : Pointer = _unit_GetTObj(hwgo);
      [*] = ;                           if (hwpo<>nil) then
      [*] = ;                           if (gObjProp[TObj(hwpo).cid][TObj(hwpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                           if (TObj(hwpo).insideofuid = 0) then
      [*] = ;                           if ((hwpass = 1) or (TObj(hwpo).orders[0].itype = gc_obj_order_type_none)) then
      [*] = ;                           gIntegerList.Add(hwgo);
      [*] = ;                        end;
      [*] = ;                        if (gIntegerList.GetCount > 0) then
      [*] = ;                        begin
      [*] = ;                           _player_ConstructBuildingList(hcph, hccid, hcsid, hcfx, hcfz, gIntegerList, True, True);
      [*] = ;                           Log('bridge-human: BUILD ' + hcsid + ' at ' + FloatToStr(hcfx) + ',' +
      [*] = ;                               FloatToStr(hcfz) + ' by ' + IntToStr(gIntegerList.GetCount) + ' workers');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', 'BUILD ' + hcsid +
      [*] = ;                                ': nobody to build it - no peasants at all');
      [*] = ;                           Log('bridge-human: BUILD ' + hcsid + ' NO WORKERS');
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'BUILD ' + hcsid +
      [*] = ;                          ': no place found within 26 around the base');
      [*] = ;                     Log('bridge-human: BUILD ' + hcsid + ' NO PLACE within 26 around base');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'TRAIN') and (hcid >= 0) then
      [*] = ;               begin
      [*] = ;                  // Producer building for this unit: the country table says which
      [*] = ;                  // building makes what. Same lookup the AI does, no aidata needed.
      [*] = ;                  var hcsid2 : String = gCountry[hccid].members[hcid];
      [*] = ;                  var hcbid : Integer = -1;
      [*] = ;                  var hci, hcjj : Integer;
      [*] = ;                  for hci := 0 to gc_country_maxfixedproduce-1 do
      [*] = ;                  for hcjj := 0 to gc_country_fixedproduce_maxcount-1 do
      [*] = ;                  if (hcbid < 0) and (SameText(gCountry[hccid].fixedproduce[hci].build[hcjj].id, hcsid2)) then
      [*] = ;                  hcbid := _unit_ConvertObjSIDToID(hccid, gCountry[hccid].fixedproduce[hci].id);
      [*] = ;                  if (hcbid >= 0) then
      [*] = ;                  begin
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hbgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hbpo : Pointer = _unit_GetTObj(hbgo);
      [*] = ;                        if (hbpo<>nil) and (TObj(hbpo).id = hcbid) and (TObj(hbpo).cid = hccid) then
      [*] = ;                        if (TObj(hbpo).bbuilt) then
      [*] = ;                        gIntegerList.Add(hbgo);
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount > 0) then
      [*] = ;                     begin
      [*] = ;                        _unit_ProduceUnit(hcph, gIntegerList, hccid, hcid, hca2, True, True, True);
      [*] = ;                        Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] + ' x' +
      [*] = ;                            IntToStr(hca2) + ' in ' + IntToStr(gIntegerList.GetCount) + ' buildings');
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'TRAIN ' +
      [*] = ;                          gCountry[hccid].members[hcid] + ': the building that makes it is not built');
      [*] = ;                     Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] + ' - no producer built yet');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'BALANCE') then
      [*] = ;               begin
      [*] = ;                  // a1: 0 food, 1 wood, 2 stone; a2: how many peasants to have on it.
      [*] = ;                  // A human slot has no resbalance table - we give the orders
      [*] = ;                  // ourselves, and only to IDLE peasants: pulling a working one off
      [*] = ;                  // its resource is what the engine does, and what ruined our early
      [*] = ;                  // episodes.
      [*] = ;                  var hbres : Integer = -1;
      [*] = ;                  if (hca1 = 0) then hbres := gc_resource_type_food;
      [*] = ;                  if (hca1 = 1) then hbres := gc_resource_type_wood;
      [*] = ;                  if (hca1 = 2) then hbres := gc_resource_type_stone;
      [*] = ;                  if (hbres >= 0) and (hca2 > 0) then
      [*] = ;                  begin
      [*] = ;                     var hbhave : Integer;
      [*] = ;                     gTmpIntList.Clear;
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hbgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hbpo : Pointer = _unit_GetTObj(hbgo);
      [*] = ;                        if (hbpo<>nil) then
      [*] = ;                        if (gObjProp[TObj(hbpo).cid][TObj(hbpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        if (TObj(hbpo).insideofuid = 0) then
      [*] = ;                        begin
      [*] = ;                           var hbot : Integer = TObj(hbpo).orders[0].itype;
      [*] = ;                           if (hbot = gc_obj_order_type_gainres) then
      [*] = ;                           begin
      [*] = ;                              var hbrp : Pointer = _res_GetTRes(TObj(hbpo).orders[0].info.trg);
      [*] = ;                              if (hbrp<>nil) and (TRes(hbrp).itype = hbres) then
      [*] = ;                              hbhave := hbhave + 1;
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           if (hbot = gc_obj_order_type_none) then
      [*] = ;                           gTmpIntList.Add(hbgo);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     // Second pass: if idle peasants are not enough, take them off ANOTHER
      [*] = ;                     // resource. Without this BALANCE could only ever place idle men, and in the
      [*] = ;                     // live game of 12.09 the model watched food stay at 3 people while it asked
      [*] = ;                     // for 12 nine ticks in a row - everyone was already busy on wood and stone.
      [*] = ;                     // The engine strips gatherers for construction, so this is the game s own
      [*] = ;                     // behaviour rather than an invention of ours.
      [*] = ;                     if (hbhave + gTmpIntList.GetCount < hca2) then
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                        if (hbhave + gTmpIntList.GetCount < hca2) then
      [*] = ;                        begin
      [*] = ;                           var hbgo2 : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                           var hbpo2 : Pointer = _unit_GetTObj(hbgo2);
      [*] = ;                           if (hbpo2<>nil) then
      [*] = ;                           if (gObjProp[TObj(hbpo2).cid][TObj(hbpo2).id].usage = gc_obj_usage_peasant) then
      [*] = ;                           if (TObj(hbpo2).insideofuid = 0) then
      [*] = ;                           if (TObj(hbpo2).orders[0].itype = gc_obj_order_type_gainres) then
      [*] = ;                           begin
      [*] = ;                              var hbrp3 : Pointer = _res_GetTRes(TObj(hbpo2).orders[0].info.trg);
      [*] = ;                              if (hbrp3<>nil) and (TRes(hbrp3).itype <> hbres) then
      [*] = ;                              gTmpIntList.Add(hbgo2);
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     if (hbhave < hca2) and (gTmpIntList.GetCount > 0) then
      [*] = ;                     begin
      [*] = ;                        // Nearest raised deposit of this type around the base.
      [*] = ;                        gIntegerList.Clear;
      [*] = ;                        // Flags are (bcheckdist, bincludefood, bincludewood, bincludestone,
      [*] = ;                        // bincludemines). Only food was on: for a whole live game BALANCE wood
      [*] = ;                        // and stone could not find a deposit at all, and the model spent eight
      [*] = ;                        // ticks writing that the order goes out but nobody starts gathering.
      [*] = ;                        // The itype filter below picks the right kind, so include all three.
      [*] = ;                        _misc_MakeListEnvironmentInRadius(hcx, hcz, 40, True, True, True, True, False, gIntegerList);
      [*] = ;                        var hbtrg : Integer = 0;
      [*] = ;                        var hbbest : Float = 1000000;
      [*] = ;                        for hck := 0 to gIntegerList.GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hbh : Integer = gIntegerList.Get(hck);
      [*] = ;                           var hbrp2 : Pointer = _res_GetTRes(hbh);
      [*] = ;                           if (hbrp2<>nil) then
      [*] = ;                           if (TRes(hbrp2).brised) and (TRes(hbrp2).itype = hbres) then
      [*] = ;                           begin
      [*] = ;                              var hbd : Float = VectorDistance(GetGameObjectPositionXByHandle(hbh), 0,
      [*] = ;                                   GetGameObjectPositionZByHandle(hbh), hcx, 0, hcz);
      [*] = ;                              if (hbd < hbbest) then
      [*] = ;                              begin
      [*] = ;                                 hbbest := hbd;
      [*] = ;                                 hbtrg := hbh;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hbtrg <> 0) then
      [*] = ;                        begin
      [*] = ;                           var hbneed : Integer = hca2 - hbhave;
      [*] = ;                           while (gTmpIntList.GetCount > hbneed) do
      [*] = ;                           gTmpIntList.Delete(gTmpIntList.GetCount-1);
      [*] = ;                           // _order_OrderUnitsToGainResource is declared INSIDE
      [*] = ;                           // progresseconomicai.inc - local to the EconomicAI state, invisible
      [*] = ;                           // from Progress. Calling it does not compile and kills the whole tick.
      [*] = ;                           // Found by bisection 12.09. lib/unit.script gives a per-unit order.
      [*] = ;                           var hbpx : Float = GetGameObjectPositionXByHandle(hbtrg);
      [*] = ;                           var hbpz : Float = GetGameObjectPositionZByHandle(hbtrg);
      [*] = ;                           for hck := 0 to gTmpIntList.GetCount-1 do
      [*] = ;                           _unit_OrderGainResource(gTmpIntList.Get(hck), hbtrg, hbpx, hbpz);
      [*] = ;                           Log('bridge-human: GATHER res' + IntToStr(hca1) + ' sent ' +
      [*] = ;                               IntToStr(gTmpIntList.GetCount) + ' peasants, had ' + IntToStr(hbhave));
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', 'GATHER res' + IntToStr(hca1) +
      [*] = ;                             ': no deposit of this kind within 40 of the base');
      [*] = ;                        Log('bridge-human: GATHER res' + IntToStr(hca1) + ' - no deposit within 40 of base');
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'BALANCE') and (hca1 >= 3) and (hca1 <= 5) and (hca2 > 0) then
      [*] = ;               begin
      [*] = ;                  // Mines: gold, iron, coal. A peasant works a mine from INSIDE,
      [*] = ;                  // so this is not a gather order but a go-inside order. Without
      [*] = ;                  // iron the barracks will not hire a single soldier, and on the
      [*] = ;                  // AI side that quietly cost us whole episodes.
      [*] = ;                  var hmrole : Integer = gc_ai_unit_minegold;
      [*] = ;                  if (hca1 = 4) then hmrole := gc_ai_unit_mineiron;
      [*] = ;                  if (hca1 = 5) then hmrole := gc_ai_unit_minecoal;
      [*] = ;                  var hmine : Integer = 0;
      [*] = ;                  var hminside : Integer;
      [*] = ;                  gTmpIntList.Clear;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hmgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hmpo : Pointer = _unit_GetTObj(hmgo);
      [*] = ;                     if (hmpo<>nil) then
      [*] = ;                     begin
      [*] = ;                        if (gObjProp[TObj(hmpo).cid][TObj(hmpo).id].airole = hmrole) then
      [*] = ;                        if (TObj(hmpo).bbuilt) and (hmine = 0) then
      [*] = ;                        hmine := hmgo;
      [*] = ;                        if (gObjProp[TObj(hmpo).cid][TObj(hmpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        begin
      [*] = ;                           if (TObj(hmpo).insideofuid <> 0) then
      [*] = ;                           hminside := hminside + 1
      [*] = ;                           else
      [*] = ;                           if (TObj(hmpo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                           gTmpIntList.Add(hmgo);
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hmine = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': no such mine is built yet');
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - no mine built');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (gTmpIntList.GetCount > 0) and (hminside < hca2) then
      [*] = ;                  begin
      [*] = ;                     var hmneed : Integer = hca2 - hminside;
      [*] = ;                     while (gTmpIntList.GetCount > hmneed) do
      [*] = ;                     gTmpIntList.Delete(gTmpIntList.GetCount-1);
      [*] = ;                     gPtrList.Clear;
      [*] = ;                     _player_OrderUnitsToGoInside(plind, gTmpIntList, gPtrList, hmine, True, False);
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' sent ' +
      [*] = ;                         IntToStr(gTmpIntList.GetCount) + ' peasants inside, had ' + IntToStr(hminside));
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'UPGRADE') then
      [*] = ;               begin
      [*] = ;                  // Upgrades without a single _ai_ call. The sid of an upgrade is
      [*] = ;                  // nation prefix + base name ('engmilfood140'), and characters 4..6
      [*] = ;                  // name the building that hosts it - the engine itself decodes it
      [*] = ;                  // that way in _ai_GetBuildingIdByBaseSID. So: match by SUFFIX,
      [*] = ;                  // then find our building of that role.
      [*] = ;                  var hupg : String = ParserGetValueByKeyByHandle(hch, hckey + 'upg');
      [*] = ;                  var huid : Integer = -1;
      [*] = ;                  var husid : String;
      [*] = ;                  var hulen : Integer = StrLength(hupg);
      [*] = ;                  if (hulen > 2) then
      [*] = ;                  for hcj := 0 to gc_country_maxupgradecount-1 do
      [*] = ;                  if (huid < 0) then
      [*] = ;                  begin
      [*] = ;                     var hus : String = gCountry[hccid].upgrade[hcj].id;
      [*] = ;                     if (StrLength(hus) > hulen) then
      [*] = ;                     if (SubStr(hus, StrLength(hus)-hulen+1, hulen) = hupg) then
      [*] = ;                     begin
      [*] = ;                        huid := hcj;
      [*] = ;                        husid := hus;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (huid < 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'UPGRADE ' + hupg +
      [*] = ;                          ': no upgrade with this name for our nation');
      [*] = ;                     Log('bridge-human: UPGRADE ' + hupg + ' - unknown for this nation');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hupart : String = SubStr(husid, 4, 3);
      [*] = ;                     var hurole : Integer = -1;
      [*] = ;                     if (hupart = 'mil') then hurole := gc_ai_unit_mill;
      [*] = ;                     if (hupart = 'cen') then hurole := gc_ai_unit_center;
      [*] = ;                     if (hupart = 'bla') then hurole := gc_ai_unit_smith;
      [*] = ;                     if (hupart = 'bar') then hurole := gc_ai_unit_ba17;
      [*] = ;                     if (hupart = 'sta') then hurole := gc_ai_unit_stable;
      [*] = ;                     if (hupart = 'aca') then hurole := gc_ai_unit_academi;
      [*] = ;                     gIntegerList.Clear;
      [*] = ;                     if (hurole >= 0) then
      [*] = ;                     for hck := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hugo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                        var hupo : Pointer = _unit_GetTObj(hugo);
      [*] = ;                        if (hupo<>nil) then
      [*] = ;                        if (gObjProp[TObj(hupo).cid][TObj(hupo).id].airole = hurole) then
      [*] = ;                        if (TObj(hupo).bbuilt) then
      [*] = ;                        gIntegerList.Add(hugo);
      [*] = ;                     end;
      [*] = ;                     if (gIntegerList.GetCount = 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', 'UPGRADE ' + hupg +
      [*] = ;                             ': the building that researches it is not built');
      [*] = ;                        Log('bridge-human: UPGRADE ' + hupg + ' - host building missing');
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     if (not _unit_CanApplyUpgradeCostBySID(hcph, hccid, husid)) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', 'UPGRADE ' + hupg +
      [*] = ;                             ': not enough resources');
      [*] = ;                        Log('bridge-human: UPGRADE ' + hupg + ' - cannot pay');
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                        _unit_MakeUpgrade(hcph, gIntegerList, huid, True, True);
      [*] = ;                        Log('bridge-human: UPGRADE ' + husid + ' started');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // --- ATTACK: same file as the AI-side bridge, executed by us ---
      [*] = ;   end;
      [*] = ;   // === END BRIDGE HUMAN COMMANDS ===