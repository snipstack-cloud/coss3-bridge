      [*] = ;   // === BRIDGE HUMAN COMMANDS: the bot plays the human side itself ===
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
      [*] = ;                  // Not enough for it? SAY SO, with the price. Until 13.09 this branch was
      [*] = ;                  // simply not taken and the bridge stayed silent: from the Python side that
      [*] = ;                  // is indistinguishable from 'the command never arrived'. The player asked
      [*] = ;                  // for mineiron=1 with 170 wood and 50 stone and saw nothing at all.
      [*] = ;                  // The price comes from the engine, so this also answers what the model could
      [*] = ;                  // never look up: what a building costs.
      [*] = ;                  if (hchave < hca2) and (not _unit_CanApplyCostByID(hccid, hcid, plind)) then
      [*] = ;                  begin
      [*] = ;                     var hcpf, hcpw, hcps, hcpg, hcpi, hcpc : Integer;
      [*] = ;                     _unit_GetCostByID(hccid, hcid, plind, hcpf, hcpw, hcps, hcpg, hcpi, hcpc);
      [*] = ;                     var hcprice : String = 'food=' + IntToStr(hcpf) + ' wood=' + IntToStr(hcpw) +
      [*] = ;                          ' stone=' + IntToStr(hcps) + ' gold=' + IntToStr(hcpg) +
      [*] = ;                          ' iron=' + IntToStr(hcpi) + ' coal=' + IntToStr(hcpc);
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'BUILD ' + hcsid +
      [*] = ;                          ': NOT ENOUGH RESOURCES. It costs ' + hcprice);
      [*] = ;                     Log('bridge-human: BUILD ' + hcsid + ' - not enough resources, costs ' + hcprice);
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
      [*] = ;                     // A MINE GOES ON A DEPOSIT, so guessing by rings is the wrong tool: twelve
      [*] = ;                     // probes per ring with step 2 stand about nine units apart at radius 17, and
      [*] = ;                     // a deposit slips between them. Since 13.09 the deposit list is filled on the
      [*] = ;                     // human slot too (block_hstate calls _ai_FillOreList), so take the nearest
      [*] = ;                     // FREE one of the right kind and put the dummy straight on it. Rings below
      [*] = ;                     // stay as the fallback for everything else - and for a mine, if this misses.
      [*] = ;                     var hcuse : Integer = gObjProp[hccid][hcid].usage;
      [*] = ;                     var hcores : Integer = -1;
      [*] = ;                     if (gObjProp[hccid][hcid].airole = gc_ai_unit_minegold) then hcores := gc_resource_type_gold;
      [*] = ;                     if (gObjProp[hccid][hcid].airole = gc_ai_unit_mineiron) then hcores := gc_resource_type_iron;
      [*] = ;                     if (gObjProp[hccid][hcid].airole = gc_ai_unit_minecoal) then hcores := gc_resource_type_coal;
      [*] = ;                     if (hcores >= 0) then
      [*] = ;                     begin
      [*] = ;                        if (gPlayer[plind].aidata.orelist.GetCount = 0) then
      [*] = ;                        _ai_FillOreList(plind);
      [*] = ;                        var hcbest : Float = 1000000;
      [*] = ;                        var hcoi : Integer;
      [*] = ;                        for hcoi := 0 to gPlayer[plind].aidata.orelist.GetCount-1 do
      [*] = ;                        begin
      [*] = ;                           var hcoh : Integer = gPlayer[plind].aidata.orelist.Get(hcoi);
      [*] = ;                           var hcopr : Pointer = _res_GetTRes(hcoh);
      [*] = ;                           if (hcopr<>nil) then
      [*] = ;                           if (TRes(hcopr).itype = hcores) then
      [*] = ;                           begin
      [*] = ;                              var hcox : Float = GetGameObjectPositionXByHandle(hcoh);
      [*] = ;                              var hcoz : Float = GetGameObjectPositionZByHandle(hcoh);
      [*] = ;                              var hcod : Float = VectorDistance(hcox, 0, hcoz, hcx, 0, hcz);
      [*] = ;                              if (hcod < hcbest) then
      [*] = ;                              begin
      [*] = ;                                 var hcdum2 : Integer = _player_CreateConstructionDummyBySID(hcmisc, hccid, hcsid, hcox, hcoz);
      [*] = ;                                 if (hcdum2 <> 0) then
      [*] = ;                                 begin
      [*] = ;                                    if (_misc_CanPlaceBuilding(hcdum2, plind, hcuse, hcox, hcoz, 0, 0.26, 0, -1, True)) then
      [*] = ;                                    begin
      [*] = ;                                       hcbest := hcod;
      [*] = ;                                       hcfound := True;
      [*] = ;                                       hcfx := hcox;
      [*] = ;                                       hcfz := hcoz;
      [*] = ;                                    end;
      [*] = ;                                    GameObjectDestroyByHandle(hcdum2);
      [*] = ;                                 end;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                        if (hcfound) then
      [*] = ;                        Log('bridge-human: BUILD ' + hcsid + ' on a deposit at ' + FloatToStr(hcfx) +
      [*] = ;                            ',' + FloatToStr(hcfz) + ' (' + FloatToStr(hcbest) + ' from base)');
      [*] = ;                     end;
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
      [*] = ;                           // NEVER take a man off an unfinished building. The second
      [*] = ;                           // pass used to grab anyone at all, and a new foundation
      [*] = ;                           // stripped the previous one bare: in base10 (16.09) that
      [*] = ;                           // happened in 4 of the 5 stalled builds - a town hall sat
      [*] = ;                           // at 92% for twelve minutes, a mill at 59% for thirteen,
      [*] = ;                           // each losing its 3 builders on the very tick after the
      [*] = ;                           // next BUILD. Parallel building is the WINNING tactic here
      [*] = ;                           // and it is measured: three stores with one builder each
      [*] = ;                           // went up in the same 38 seconds as one. So the answer is
      [*] = ;                           // not "do not start another", it is "do not rob the one
      [*] = ;                           // already standing". Gatherers may still be taken.
      [*] = ;                           if (TObj(hwpo).orders[0].itype <> gc_obj_order_type_build) then
      [*] = ;                           if (TObj(hwpo).orders[0].itype <> gc_obj_order_type_repair) then
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
      [*] = ;                        // The engine ANSWERS whether it took the order, and until
      [*] = ;                        // 17.09 the bridge threw that answer away: it logged the
      [*] = ;                        // order and called it a day. Series base14: 345 of 348
      [*] = ;                        // TRAIN orders were infinite, and a refused one looked
      [*] = ;                        // exactly like a working conveyor.
      [*] = ;                        var hctok : Boolean = _unit_ProduceUnit(hcph, gIntegerList,
      [*] = ;                             hccid, hcid, hca2, True, True, True);
      [*] = ;                        if (hctok) then
      [*] = ;                        Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] + ' x' +
      [*] = ;                            IntToStr(hca2) + ' in ' + IntToStr(gIntegerList.GetCount) + ' buildings')
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', 'TRAIN ' +
      [*] = ;                                gCountry[hccid].members[hcid] + ': THE GAME DID NOT TAKE ' +
      [*] = ;                                'THE ORDER. The building is there, so look at the queue ' +
      [*] = ;                                '(train_now) and at the food');
      [*] = ;                           Log('bridge-human: TRAIN ' + gCountry[hccid].members[hcid] +
      [*] = ;                                ' - REFUSED by the game');
      [*] = ;                        end;
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
      [*] = ;                  // Mines: gold, iron, coal. A peasant works a mine from INSIDE, so this is
      [*] = ;                  // not a gather order but a go-inside order.
      [*] = ;                  //
      [*] = ;                  // 15.09: this branch had two blind spots, both found by counting traces.
      [*] = ;                  // 'Already inside' counted peasants inside ANY building, so three men in the
      [*] = ;                  // iron mine turned 'BALANCE gold 3' into a silent no-op. And only the FIRST
      [*] = ;                  // mine of the kind was ever filled - a second gold mine stayed empty forever.
      [*] = ;                  // Now both the counting and the filling go mine by mine, the way the engine
      [*] = ;                  // fills them itself in _ai_FillMines (progresseconomicai.inc:1305).
      [*] = ;                  var hmrole : Integer = gc_ai_unit_minegold;
      [*] = ;                  if (hca1 = 4) then hmrole := gc_ai_unit_mineiron;
      [*] = ;                  if (hca1 = 5) then hmrole := gc_ai_unit_minecoal;
      [*] = ;                  var hmk, hmk2 : Integer;
      [*] = ;                  var hmine : Integer = 0;
      [*] = ;                  var hminside : Integer = 0;
      [*] = ;                  var hmfree : Integer = 0;
      [*] = ;                  // First pass: mines of this kind built, men already inside THEM, and men
      [*] = ;                  // free to be sent at all.
      [*] = ;                  for hmk := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hmgo : Integer = GetGameObjectHandleByIndex(hmk, hcph);
      [*] = ;                     var hmpo : Pointer = _unit_GetTObj(hmgo);
      [*] = ;                     if (hmpo<>nil) then
      [*] = ;                     begin
      [*] = ;                        if (gObjProp[TObj(hmpo).cid][TObj(hmpo).id].airole = hmrole) then
      [*] = ;                        if (TObj(hmpo).bbuilt) then
      [*] = ;                        hmine := hmine + 1;
      [*] = ;                        if (gObjProp[TObj(hmpo).cid][TObj(hmpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                        begin
      [*] = ;                           if (TObj(hmpo).insideofuid <> 0) then
      [*] = ;                           begin
      [*] = ;                              var hmih : Integer = GetGameObjectHandleByUniqueId(TObj(hmpo).insideofuid);
      [*] = ;                              var hmip : Pointer = _unit_GetTObj(hmih);
      [*] = ;                              if (hmip<>nil) then
      [*] = ;                              if (gObjProp[TObj(hmip).cid][TObj(hmip).id].airole = hmrole) then
      [*] = ;                              hminside := hminside + 1;
      [*] = ;                           end
      [*] = ;                           else
      [*] = ;                           if (TObj(hmpo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                           hmfree := hmfree + 1;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  // Silence is indistinguishable from doing nothing: every refusal says why,
      [*] = ;                  // and the reason goes back into the next request.
      [*] = ;                  if (hmine = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': no such mine is built yet');
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - no mine built');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hminside >= hca2) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': ' + IntToStr(hminside) + ' already work that mine, asked for ' + IntToStr(hca2));
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - already inside ' + IntToStr(hminside));
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hmfree = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                          ': no idle peasant to send, and a busy one is not taken away');
      [*] = ;                     Log('bridge-human: MINE res' + IntToStr(hca1) + ' - no idle peasants');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hmsent : Integer = 0;
      [*] = ;                     var hmroom : Integer = 0;
      [*] = ;                     // Second pass: fill mine by mine, each up to its OWN free places. The
      [*] = ;                     // formula is the engine's: places minus those inside minus those already
      [*] = ;                     // on their way (insidereserved).
      [*] = ;                     for hmk := 0 to hcobjn-1 do
      [*] = ;                     begin
      [*] = ;                        var hmbo : Integer = GetGameObjectHandleByIndex(hmk, hcph);
      [*] = ;                        var hmbp : Pointer = _unit_GetTObj(hmbo);
      [*] = ;                        if (hmbp<>nil) then
      [*] = ;                        if (gObjProp[TObj(hmbp).cid][TObj(hmbp).id].airole = hmrole) then
      [*] = ;                        if (TObj(hmbp).bbuilt) then
      [*] = ;                        if (hminside + hmsent < hca2) then
      [*] = ;                        begin
      [*] = ;                           var hmuid : Integer = GetGameObjectUniqueIdByHandle(hmbo);
      [*] = ;                           var hmthis : Integer = 0;
      [*] = ;                           for hmk2 := 0 to hcobjn-1 do
      [*] = ;                           begin
      [*] = ;                              var hmgo2 : Integer = GetGameObjectHandleByIndex(hmk2, hcph);
      [*] = ;                              var hmpo2 : Pointer = _unit_GetTObj(hmgo2);
      [*] = ;                              if (hmpo2<>nil) then
      [*] = ;                              if (gObjProp[TObj(hmpo2).cid][TObj(hmpo2).id].usage = gc_obj_usage_peasant) then
      [*] = ;                              if (TObj(hmpo2).insideofuid = hmuid) then
      [*] = ;                              hmthis := hmthis + 1;
      [*] = ;                           end;
      [*] = ;                           hmroom := gObjProp[TObj(hmbp).cid][TObj(hmbp).id].peasantabsorber +
      [*] = ;                                TObj(hmbp).individual.addpeasantabsorber - hmthis - TObj(hmbp).insidereserved;
      [*] = ;                           var hmneed : Integer = hca2 - hminside - hmsent;
      [*] = ;                           if (hmroom > hmneed) then
      [*] = ;                           hmroom := hmneed;
      [*] = ;                           if (hmroom > 0) then
      [*] = ;                           begin
      [*] = ;                              gTmpIntList.Clear;
      [*] = ;                              for hmk2 := 0 to hcobjn-1 do
      [*] = ;                              if (gTmpIntList.GetCount < hmroom) then
      [*] = ;                              begin
      [*] = ;                                 var hmgo3 : Integer = GetGameObjectHandleByIndex(hmk2, hcph);
      [*] = ;                                 var hmpo3 : Pointer = _unit_GetTObj(hmgo3);
      [*] = ;                                 if (hmpo3<>nil) then
      [*] = ;                                 if (gObjProp[TObj(hmpo3).cid][TObj(hmpo3).id].usage = gc_obj_usage_peasant) then
      [*] = ;                                 if (TObj(hmpo3).insideofuid = 0) then
      [*] = ;                                 if (TObj(hmpo3).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                                 gTmpIntList.Add(hmgo3);
      [*] = ;                              end;
      [*] = ;                              if (gTmpIntList.GetCount > 0) then
      [*] = ;                              begin
      [*] = ;                                 gPtrList.Clear;
      [*] = ;                                 _player_OrderUnitsToGoInside(plind, gTmpIntList, gPtrList, hmbo, True, False);
      [*] = ;                                 hmsent := hmsent + gTmpIntList.GetCount;
      [*] = ;                                 Log('bridge-human: MINE res' + IntToStr(hca1) + ' sent ' +
      [*] = ;                                     IntToStr(gTmpIntList.GetCount) + ' into one mine, had inside ' +
      [*] = ;                                     IntToStr(hmthis));
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (hmsent = 0) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', 'BALANCE res' + IntToStr(hca1) +
      [*] = ;                             ': every mine of that kind is full, build one more');
      [*] = ;                        Log('bridge-human: MINE res' + IntToStr(hca1) + ' - all mines full');
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               // SEED: order one more field at every mill.
      [*] = ;               //
      [*] = ;               // A field is a UNIT the mill produces (usage = gc_obj_usage_field), not a
      [*] = ;               // button that costs nothing: it is priced at 5 gold (unit.script:1692), and
      [*] = ;               // the engine turns the order into an actual field in doprogressorders.inc:130
      [*] = ;               // by calling _unit_DoSeedWheat. So we place the same ORDER a player places -
      [*] = ;               // calling DoSeedWheat directly would skip both the queue and the price.
      [*] = ;               //
      [*] = ;               // The FIRST field is sown by the game itself when the mill is finished
      [*] = ;               // (ontagstates.inc:140). What nobody did on the human slot is sow AGAIN once
      [*] = ;               // that field is reaped - and that is where the hunger came from: food only
      [*] = ;               // fell, and below 500 the whole endless production stops.
      [*] = ;               if (hccmd = 'SEED') then
      [*] = ;               begin
      [*] = ;                  // sid must be a VARIABLE: _unit_ConvertObjSIDToID takes it as
      [*] = ;                  // 'var sid : String' (unit.script:438), a literal does not compile.
      [*] = ;                  // On 13.09 that killed the whole Progress tick - with it the economy
      [*] = ;                  // of BOTH players: nothing was being built anywhere.
      [*] = ;                  var hcfsid : String = 'field';
      [*] = ;                  var hcfid : Integer = _unit_ConvertObjSIDToID(hccid, hcfsid);
      [*] = ;                  gTmpIntList.Clear;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hcmh : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hcmp : Pointer = _unit_GetTObj(hcmh);
      [*] = ;                     if (hcmp<>nil) then
      [*] = ;                     if (gObjProp[TObj(hcmp).cid][TObj(hcmp).id].airole = gc_ai_unit_mill) then
      [*] = ;                     if (TObj(hcmp).bbuilt) then
      [*] = ;                     gTmpIntList.Add(hcmh);
      [*] = ;                  end;
      [*] = ;                  if (gTmpIntList.GetCount = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why',
      [*] = ;                          'SEED: no mill is built yet - fields are sown at a mill');
      [*] = ;                     Log('bridge-human: SEED - no mill built');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  if (hcfid <= 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'SEED: this nation has no field object');
      [*] = ;                     Log('bridge-human: SEED - no field object for this nation');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     _unit_ProduceUnit(hcph, gTmpIntList, hccid, hcfid, 1, True, True, True);
      [*] = ;                     Log('bridge-human: SEED ordered at ' + IntToStr(gTmpIntList.GetCount) + ' mills');
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (hccmd = 'FORMATION') then
      [*] = ;               begin
      [*] = ;                  // A formation is the last term of the readiness the player
      [*] = ;                  // named, and the only one the bridge could not touch at all.
      [*] = ;                  // The engine gives the bonus ONLY to an officer squad: both an
      [*] = ;                  // officer and a drummer are required (_ai_CreateOfficerSquad,
      [*] = ;                  // progresswarai.inc:3597), and the 'NB' shapes in formations.cfg
      [*] = ;                  // carry zeroes. The set of shapes belongs to the officer type,
      [*] = ;                  // so we ask the country table, exactly as the native AI does,
      [*] = ;                  // and take the most compact one by width+height.
      [*] = ;                  var hfoff : Integer = 0;
      [*] = ;                  var hfdrum : Integer = 0;
      [*] = ;                  gIntegerList.Clear;
      [*] = ;                  for hck := 0 to hcobjn-1 do
      [*] = ;                  begin
      [*] = ;                     var hfgo : Integer = GetGameObjectHandleByIndex(hck, hcph);
      [*] = ;                     var hfp : Pointer = _unit_GetTObj(hfgo);
      [*] = ;                     if (hfp<>nil) then
      [*] = ;                     begin
      [*] = ;                        var hfrole : Integer = gObjProp[TObj(hfp).cid][TObj(hfp).id].airole;
      [*] = ;                        var hfu : Integer = gObjProp[TObj(hfp).cid][TObj(hfp).id].usage;
      [*] = ;                        if (hfoff = 0) and (hfrole = gc_ai_unit_officer17) then
      [*] = ;                        hfoff := hfgo;
      [*] = ;                        if (hfdrum = 0) and (hfrole = gc_ai_unit_drummer17) then
      [*] = ;                        hfdrum := hfgo;
      [*] = ;                        if (hfu = gc_obj_usage_lightinfantry) or (hfu = gc_obj_usage_weak) or
      [*] = ;                           (hfu = gc_obj_usage_grenadier) or (hfu = gc_obj_usage_shooter) or
      [*] = ;                           (hfu = gc_obj_usage_archer) then
      [*] = ;                        gIntegerList.Add(hfgo);
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;                  if (hfoff = 0) or (hfdrum = 0) then
      [*] = ;                  begin
      [*] = ;                     ParserSetValueByKeyByHandle(hfl, 'why', 'FORMATION: a bonus ' +
      [*] = ;                          'formation needs BOTH an officer and a drummer. Have ' +
      [*] = ;                          'officers: ' + IntToStr(hfoff) + ', drummers: ' + IntToStr(hfdrum) +
      [*] = ;                          ' (0 means none free). Train officer17 and drummer17 first');
      [*] = ;                     Log('bridge-human: FORMATION - no officer or no drummer');
      [*] = ;                  end
      [*] = ;                  else
      [*] = ;                  begin
      [*] = ;                     var hfsid : String = GetGameObjectBaseNameByHandle(hfoff);
      [*] = ;                     var hfoi : Integer = _country_GetOfficersIndexByOfficerSID(hccid, hfsid);
      [*] = ;                     var hfform : Integer = -1;
      [*] = ;                     var hfbest : Integer = -1;
      [*] = ;                     var hfneed : Integer = 1000000;
      [*] = ;                     var hfmen : Integer = gIntegerList.GetCount;
      [*] = ;                     // Choose a USEFUL shape that FITS, not the most compact one.
      [*] = ;                     // Live game 16.09: 'most compact' picked the degenerate
      [*] = ;                     // 'none' formation - squad built, bonuses all zero. A shape
      [*] = ;                     // with no bonus at all (the 'NB' family and 'none') is worth
      [*] = ;                     // nothing, and a shape needing more men than we brought
      [*] = ;                     // cannot form. So: skip the zero ones, keep those that fit,
      [*] = ;                     // and among them take the one asking for the MOST men - the
      [*] = ;                     // wider line is the stronger one.
      [*] = ;                     if (hfoi >= 0) then
      [*] = ;                     for hcj := 0 to gc_country_maxformationcount-1 do
      [*] = ;                     begin
      [*] = ;                        var hfms : String = gCountry[hccid].officers[hfoi].formations[hcj].masks[0];
      [*] = ;                        if (hfms <> '') then
      [*] = ;                        begin
      [*] = ;                           var hffi : Integer = _misc_GetFormationIndexBySID(hfms);
      [*] = ;                           if (hffi >= 0) then
      [*] = ;                           begin
      [*] = ;                              var hfbon : Integer = gFormation[hffi].bonusdamage +
      [*] = ;                                   gFormation[hffi].bonusshield +
      [*] = ;                                   gFormation[hffi].bonusdamagehold +
      [*] = ;                                   gFormation[hffi].bonusshieldhold;
      [*] = ;                              var hfcnt : Integer = gFormation[hffi].countunits;
      [*] = ;                              if (hfbon > 0) and (hfcnt < hfneed) then
      [*] = ;                              hfneed := hfcnt;
      [*] = ;                              if (hfbon > 0) and (hfcnt <= hfmen) and (hfcnt > hfbest) then
      [*] = ;                              begin
      [*] = ;                                 hfbest := hfcnt;
      [*] = ;                                 hfform := hffi;
      [*] = ;                              end;
      [*] = ;                           end;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                     if (hfform < 0) then
      [*] = ;                     begin
      [*] = ;                        // Two different reasons, and they must not be confused:
      [*] = ;                        // 'too few men' is fixable this very tick, 'no formations'
      [*] = ;                        // is not fixable at all.
      [*] = ;                        if (hfneed < 1000000) then
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', 'FORMATION: too ' +
      [*] = ;                                'few men. The smallest formation with a bonus needs ' +
      [*] = ;                                IntToStr(hfneed) + ', you brought ' + IntToStr(hfmen));
      [*] = ;                           Log('bridge-human: FORMATION - need ' + IntToStr(hfneed) +
      [*] = ;                                ' men, have ' + IntToStr(hfmen));
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', 'FORMATION: this ' +
      [*] = ;                                'officer has no formation of his own in the country table');
      [*] = ;                           Log('bridge-human: FORMATION - officer has no formations');
      [*] = ;                        end;
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                        var hfsq : Pointer = _player_CreateSquad(hcph, hfform, hfoff,
      [*] = ;                             hfdrum, gIntegerList, True, True);
      [*] = ;                        if (hfsq = nil) then
      [*] = ;                        begin
      [*] = ;                           ParserSetValueByKeyByHandle(hfl, 'why', 'FORMATION: the ' +
      [*] = ;                                'game refused to build the squad');
      [*] = ;                           Log('bridge-human: FORMATION - CreateSquad returned nil');
      [*] = ;                        end
      [*] = ;                        else
      [*] = ;                        begin
      [*] = ;                           // CreateSquad DOES NOT set the formation: it only takes
      [*] = ;                           // the size and the facing out of it (player.script:960).
      [*] = ;                           // The shape itself is applied separately, and without
      [*] = ;                           // this call the squad stands in 'none' with zero bonuses
      [*] = ;                           // - live game 16.09, 54 men in a squad and +0 to
      [*] = ;                           // everything. The engine's own code does the same:
      [*] = ;                           // progresseconomicai.inc:1110.
      [*] = ;                           _player_SetSquadFormation(hcph, TSquad(hfsq).fIndex,
      [*] = ;                                hfform, True, False);
      [*] = ;                           Log('bridge-human: FORMATION ' + gFormation[hfform].sid +
      [*] = ;                                ' built of ' + IntToStr(gIntegerList.GetCount) + ' men');
      [*] = ;                        end;
      [*] = ;                     end;
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
      [*] = ;                     // The price, so a refusal names a NUMBER. Read straight from the
      [*] = ;                     // nation table by OUR index: _country_GetUpgradeCostBySID skips the
      [*] = ;                     // lookup for index 0 (country.script:760 tests upgid>0).
      [*] = ;                     //
      [*] = ;                     // The check itself stays the engine's. 16.09 I replaced it with my own
      [*] = ;                     // comparison, reading gPlayer[].res as a plain number - and mil.1, worth
      [*] = ;                     // 750 food at 3733 in store, was refused. In this language these fields
      [*] = ;                     // are read through 'not' (block_hstate does exactly that for 'food'),
      [*] = ;                     // so the engine's 'not res >= cost' is correct and mine was not.
      [*] = ;                     var hucf : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_food];
      [*] = ;                     var hucw : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_wood];
      [*] = ;                     var hucs : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_stone];
      [*] = ;                     var hucg : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_gold];
      [*] = ;                     var huci : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_iron];
      [*] = ;                     var hucc : Integer = gCountry[hccid].upgrade[huid].price[gc_resource_type_coal];
      [*] = ;                     var huprice : String = 'food=' + IntToStr(hucf) + ' wood=' + IntToStr(hucw) +
      [*] = ;                          ' stone=' + IntToStr(hucs) + ' gold=' + IntToStr(hucg) +
      [*] = ;                          ' iron=' + IntToStr(huci) + ' coal=' + IntToStr(hucc);
      [*] = ;                     if (not _unit_CanApplyUpgradeCostBySID(hcph, hccid, husid)) then
      [*] = ;                     begin
      [*] = ;                        ParserSetValueByKeyByHandle(hfl, 'why', 'UPGRADE ' + hupg +
      [*] = ;                             ': NOT ENOUGH RESOURCES. It costs ' + huprice);
      [*] = ;                        Log('bridge-human: UPGRADE ' + hupg + ' - cannot pay, costs ' + huprice);
      [*] = ;                     end
      [*] = ;                     else
      [*] = ;                     begin
      [*] = ;                        _unit_MakeUpgrade(hcph, gIntegerList, huid, True, True);
      [*] = ;                        Log('bridge-human: UPGRADE ' + husid + ' started, costs ' + huprice);
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      // --- ATTACK: same file as the AI-side bridge, executed by us ---
      [*] = ;      var hapath : String = '@@OUT@@coss3_atk_P' + IntToStr(plind) + '.dat';
      [*] = ;      if IsFileExists(hapath) then
      [*] = ;      begin
      [*] = ;         var hah : Integer = ParserSelectByKey('br_hatk');
      [*] = ;         if (hah = 0) then
      [*] = ;         hah := ParserCreate('br_hatk');
      [*] = ;         ParserClearByHandle(hah);
      [*] = ;         var haok : Boolean = ParserLoadFromFileByHandle(hah, hapath);
      [*] = ;         DeleteFileStream(hapath);
      [*] = ;         // Mode is read HERE, before the condition that uses it. First try put
      [*] = ;         // the declaration inside the block and the test in its own condition -
      [*] = ;         // a name used before it is declared. The whole Progress tick stopped
      [*] = ;         // compiling, exactly as PROGRESS.md 5.4 describes.
      [*] = ;         var hamode : String = ParserGetValueByKeyByHandle(hah, 'mode');
      [*] = ;         if (haok) and ((not gbool_peacemode) or (hamode = 'move')) then
      [*] = ;         begin
      [*] = ;            var hawant : Integer = ParserGetIntValueByKeyByHandle(hah, 'count');
      [*] = ;            var hatrg : String = ParserGetValueByKeyByHandle(hah, 'target');
      [*] = ;            // MOVE: the same order file, only the mode differs. A player moves his
      [*] = ;            // troops wherever he likes with a click and is not obliged to send them
      [*] = ;            // into battle; the bot had ATTACK and nothing else, so a manoeuvre -
      [*] = ;            // stand aside, take a place in advance - was physically impossible.
      [*] = ;            // Empty mode means attack: an older client sends no such key.
      [*] = ;            var haph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;            var han : Integer = GetPlayerGameObjectsCountByHandle(haph);
      [*] = ;            // Our own anchor point: the ATTACK file is read outside the command
      [*] = ;            // block, so it cannot borrow its variables. Centre if we have one,
      [*] = ;            // otherwise any object of ours.
      [*] = ;            var hax, haz : Float;
      [*] = ;            var habk : Integer;
      [*] = ;            var haanchor : Boolean = False;
      [*] = ;            for habk := 0 to han-1 do
      [*] = ;            if (not haanchor) then
      [*] = ;            begin
      [*] = ;               var habgo : Integer = GetGameObjectHandleByIndex(habk, haph);
      [*] = ;               var habpo : Pointer = _unit_GetTObj(habgo);
      [*] = ;               if (habpo<>nil) then
      [*] = ;               if (gObjProp[TObj(habpo).cid][TObj(habpo).id].airole = gc_ai_unit_center) then
      [*] = ;               begin
      [*] = ;                  hax := GetGameObjectPositionXByHandle(habgo);
      [*] = ;                  haz := GetGameObjectPositionZByHandle(habgo);
      [*] = ;                  haanchor := True;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (not haanchor) and (han > 0) then
      [*] = ;            begin
      [*] = ;               var haany : Integer = GetGameObjectHandleByIndex(0, haph);
      [*] = ;               hax := GetGameObjectPositionXByHandle(haany);
      [*] = ;               haz := GetGameObjectPositionZByHandle(haany);
      [*] = ;            end;
      [*] = ;            var hak : Integer;
      [*] = ;            // Idle soldiers only: a unit already marching is left alone, otherwise
      [*] = ;            // a new order regroups the wave and it stalls - learned the hard way.
      [*] = ;            gIntegerList.Clear;
      [*] = ;            for hak := 0 to han-1 do
      [*] = ;            if (gIntegerList.GetCount < hawant) then
      [*] = ;            begin
      [*] = ;               var hago : Integer = GetGameObjectHandleByIndex(hak, haph);
      [*] = ;               var hapo : Pointer = _unit_GetTObj(hago);
      [*] = ;               if (hapo<>nil) then
      [*] = ;               begin
      [*] = ;                  var hau : Integer = gObjProp[TObj(hapo).cid][TObj(hapo).id].usage;
      [*] = ;                  if (not gObjProp[TObj(hapo).cid][TObj(hapo).id].bbuilding) then
      [*] = ;                  if (hau <> gc_obj_usage_peasant) and (hau <> gc_obj_usage_none) then
      [*] = ;                  if (TObj(hapo).orders[0].itype = gc_obj_order_type_none) then
      [*] = ;                  gIntegerList.Add(hago);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // Where to go. The model chooses: peasants (the objective), base, or army.
      [*] = ;            var hatx, hatz : Float;
      [*] = ;            var hafound : Boolean = False;
      [*] = ;            var habest : Float = 1000000;
      [*] = ;            var hapl : Integer;
      [*] = ;            for hapl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;            if (gPlayer[hapl].bexists) and (hapl <> plind) then
      [*] = ;            if ((gPlayer[plind].enemyPlMask and gPlayer[hapl].myPlMask) <> 0) then
      [*] = ;            begin
      [*] = ;               var haeph : Integer = GetPlayerHandleByIndex(hapl);
      [*] = ;               var haen : Integer = GetPlayerGameObjectsCountByHandle(haeph);
      [*] = ;               var haj : Integer;
      [*] = ;               for haj := 0 to haen-1 do
      [*] = ;               begin
      [*] = ;                  var haeg : Integer = GetGameObjectHandleByIndex(haj, haeph);
      [*] = ;                  var haep : Pointer = _unit_GetTObj(haeg);
      [*] = ;                  if (haep<>nil) then
      [*] = ;                  begin
      [*] = ;                     var haeu : Integer = gObjProp[TObj(haep).cid][TObj(haep).id].usage;
      [*] = ;                     var haeb : Boolean = gObjProp[TObj(haep).cid][TObj(haep).id].bbuilding;
      [*] = ;                     var hatake : Boolean = False;
      [*] = ;                     if (hatrg = 'peasants') and (haeu = gc_obj_usage_peasant) then hatake := True;
      [*] = ;                     if (hatrg <> 'peasants') and (haeb) then hatake := True;
      [*] = ;                     if (hatake) then
      [*] = ;                     begin
      [*] = ;                        var haex : Float = GetGameObjectPositionXByHandle(haeg);
      [*] = ;                        var haez : Float = GetGameObjectPositionZByHandle(haeg);
      [*] = ;                        var had : Float = VectorDistance(haex, 0, haez, hax, 0, haz);
      [*] = ;                        if (had < habest) then
      [*] = ;                        begin
      [*] = ;                           habest := had;
      [*] = ;                           hatx := haex;
      [*] = ;                           hatz := haez;
      [*] = ;                           hafound := True;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            // 'home' is our own anchor: the only target that needs no enemy at all.
      [*] = ;            if (hatrg = 'home') then
      [*] = ;            begin
      [*] = ;               hatx := hax;
      [*] = ;               hatz := haz;
      [*] = ;               hafound := True;
      [*] = ;            end;
      [*] = ;            if (hafound) and (gIntegerList.GetCount > 0) then
      [*] = ;            begin
      [*] = ;               // ONE GROUP PER WAVE. The name used to be the same for every wave, and
      [*] = ;               // GroupClearGameObjectsByHandle threw out of it those ALREADY MARCHING:
      [*] = ;               // the first wave lost its group and its order the moment the second one
      [*] = ;               // left. The numbers show it plainly - 14.09, nine games: 35 waves, 1139
      [*] = ;               // soldiers sent, zero enemy peasants killed AND zero losses of our own.
      [*] = ;               // The army went out and never arrived. HANDOFF describes the same thing
      [*] = ;               // on the AI side, where the cause sat elsewhere.
      [*] = ;               // Eight names in a circle: no more waves than that live at once.
      [*] = ;               var hagname : String = 'coss3_wave_' + IntToStr(Round(GetGameTime) mod 8);
      [*] = ;               var hagr : Integer = _misc_GetOrCreateGroupByName(haph, hagname);
      [*] = ;               GroupClearGameObjectsByHandle(hagr);
      [*] = ;               for hak := 0 to gIntegerList.GetCount-1 do
      [*] = ;               GroupAddGameObjectByHandle(hagr, gIntegerList.Get(hak));
      [*] = ;               _group_Initialize(hagr, nil);
      [*] = ;               if (hamode = 'move') then
      [*] = ;               begin
      [*] = ;                  // No _unit_ListSetSearchEnemy here on purpose: that is what turns a
      [*] = ;                  // walk into a hunt. Mode default is how the game itself moves a
      [*] = ;                  // group - player.script:2503.
      [*] = ;                  _player_SetGroupPosition(haph, hagr, -1, hatx, hatz, hatx, hatz, 0, 1,
      [*] = ;                       False, False, True, True, gc_obj_order_move_mode_default);
      [*] = ;                  Log('bridge-human: MOVE ' + IntToStr(gIntegerList.GetCount) + ' target=' + hatrg +
      [*] = ;                      ' at ' + FloatToStr(hatx) + ',' + FloatToStr(hatz));
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (_unit_ListSetSearchEnemy(haph, gIntegerList, True, True)) then
      [*] = ;               begin
      [*] = ;                  _player_SetGroupPosition(haph, hagr, -1, hatx, hatz, hatx, hatz, 0, 1,
      [*] = ;                       False, False, True, True, gc_obj_order_move_mode_attack);
      [*] = ;                  Log('bridge-human: ATTACK ' + IntToStr(gIntegerList.GetCount) + ' target=' + hatrg +
      [*] = ;                      ' at ' + FloatToStr(hatx) + ',' + FloatToStr(hatz));
      [*] = ;                  // Wave size goes into a NAMED PARSER, not into a group. 14.09 the
      [*] = ;                  // 'one group per wave' fix renamed the groups to coss3_wave_0..7,
      [*] = ;                  // and block_hstate went on counting the old coss3_bridge_wave -
      [*] = ;                  // empty forever. wave_sent was zero in EVERY run since, and the
      [*] = ;                  // model read 'no waves at all' right after sending one.
      [*] = ;                  // A named parser lives between ticks and knows nothing of groups.
      [*] = ;                  var hawp : Integer = ParserSelectByKey('br_hwave');
      [*] = ;                  if (hawp = 0) then
      [*] = ;                  hawp := ParserCreate('br_hwave');
      [*] = ;                  ParserSetIntValueByKeyByHandle(hawp, 'sent', gIntegerList.GetCount);
      [*] = ;               end;
      [*] = ;            end
      [*] = ;            else
      [*] = ;            Log('bridge-human: ATTACK skipped - soldiers ' + IntToStr(gIntegerList.GetCount) +
      [*] = ;                ', target found ' + BoolToStr(hafound));
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE HUMAN COMMANDS ===