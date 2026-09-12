      [*] = ;   // === PEACE-TIME BUILD ORDER BRIDGE: import commands ===
      [*] = ;   if (bai) and (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;   begin
      [*] = ;      var brcmdpath : String = '@@OUT@@coss3_cmd_P' + IntToStr(plind) + '.dat';
      [*] = ;      if IsFileExists(brcmdpath) then
      [*] = ;      begin
      [*] = ;         var brcid2 : Integer = gPlayer[plind].cid;
      [*] = ;         var hcmd : Integer = ParserSelectByKey('br_cmd');
      [*] = ;         if (hcmd = 0) then
      [*] = ;         hcmd := ParserCreate('br_cmd');
      [*] = ;         ParserClearByHandle(hcmd);
      [*] = ;         var brcmdcount : Integer;    // must live outside the block below
      [*] = ;         if ParserLoadFromFileByHandle(hcmd, brcmdpath) then
      [*] = ;         begin
      [*] = ;            brcmdcount := ParserGetIntValueByKeyByHandle(hcmd, 'count');
      [*] = ;            var bri : Integer;
      [*] = ;            for bri := 0 to brcmdcount - 1 do
      [*] = ;            begin
      [*] = ;               var brkey : String = IntToStr(bri) + '_';
      [*] = ;               var brcmd : String = ParserGetValueByKeyByHandle(hcmd, brkey + 'cmd');
      [*] = ;               var brarg1 : Integer = ParserGetIntValueByKeyByHandle(hcmd, brkey + 'a1');
      [*] = ;               var brarg2 : Integer = ParserGetIntValueByKeyByHandle(hcmd, brkey + 'a2');
      [*] = ;               if brcmd = 'BUILD' then
      [*] = ;               begin
      [*] = ;                  // declarative: a2 = desired TOTAL count of this building role
      [*] = ;                  // (house is special-cased inside _ai_TryUnit: it caps by ideas-in-progress < 3)
      [*] = ;                  if (brarg1 = gc_ai_unit_center) or (brarg1 = gc_ai_unit_mill) or
      [*] = ;                     (brarg1 = gc_ai_unit_ba17) or (brarg1 = gc_ai_unit_ba18) or
      [*] = ;                     (brarg1 = gc_ai_unit_stable) or (brarg1 = gc_ai_unit_smith) or
      [*] = ;                     (brarg1 = gc_ai_unit_academi) or (brarg1 = gc_ai_unit_market) or
      [*] = ;                     (brarg1 = gc_ai_unit_house) or (brarg1 = gc_ai_unit_minegold) or
      [*] = ;                     (brarg1 = gc_ai_unit_mineiron) or (brarg1 = gc_ai_unit_minecoal) or
      [*] = ;                     (brarg1 = gc_ai_unit_store) or (brarg1 = gc_ai_unit_tower) then
      [*] = ;                  _ai_TryUnit(plind, brcid2, brarg1, brarg2, false);
      [*] = ;               end
      [*] = ;               else if brcmd = 'TRAIN' then
      [*] = ;                  _ai_TryUnit(plind, brcid2, brarg1, brarg2, false)
      [*] = ;               else if brcmd = 'BUILDERS' then
      [*] = ;               begin
      [*] = ;                  // a1 = cap on peasants per construction site. The engine always calls
      [*] = ;                  // buildprojects[i].maxpeasants builders (that number comes from the
      [*] = ;                  // building geometry, gCustomObjPoints.builderCount) and, when free
      [*] = ;                  // peasants are not enough, rips the rest off mining by a spiral search
      [*] = ;                  // around the site. That is what emptied the mines in the first minute
      [*] = ;                  // of every early episode. Repeat the command every tick: new projects
      [*] = ;                  // appear with the engine default.
      [*] = ;                  var brbi : Integer;
      [*] = ;                  if (brarg1 > 0) then
      [*] = ;                  for brbi := 0 to gc_ai_max_construction_sites-1 do
      [*] = ;                  if (gPlayer[plind].aidata.buildprojects[brbi].used) and
      [*] = ;                     (gPlayer[plind].aidata.buildprojects[brbi].maxpeasants > brarg1) then
      [*] = ;                  gPlayer[plind].aidata.buildprojects[brbi].maxpeasants := brarg1;
      [*] = ;               end
      [*] = ;               else if brcmd = 'BALANCE' then
      [*] = ;               begin
      [*] = ;                  // Доля крестьян на ресурс. Работает потому, что этот блок
      [*] = ;                  // вставлен СРАЗУ ПОСЛЕ _ai_ResourcesDistributionScript:
      [*] = ;                  // нативное распределение выставляется каждый тик, и наше
      [*] = ;                  // значение должно идти после него, иначе будет затёрто.
      [*] = ;                  // a1: 0 еда, 1 дерево, 2 камень, 3 золото, 4 железо, 5 уголь.
      [*] = ;                  var brres : Integer = -1;
      [*] = ;                  if (brarg1 = 0) then brres := gc_resource_type_food
      [*] = ;                  else if (brarg1 = 1) then brres := gc_resource_type_wood
      [*] = ;                  else if (brarg1 = 2) then brres := gc_resource_type_stone
      [*] = ;                  else if (brarg1 = 3) then brres := gc_resource_type_gold
      [*] = ;                  else if (brarg1 = 4) then brres := gc_resource_type_iron
      [*] = ;                  else if (brarg1 = 5) then brres := gc_resource_type_coal;
      [*] = ;                  if (brres <> -1) and (brarg2 >= 0) and (brarg2 <= 100) then
      [*] = ;                  _ai_SetResouceBalance(plind, brres, brarg2, -1, -1);
      [*] = ;               end
      [*] = ;               else if brcmd = 'UPGRADE' then
      [*] = ;               begin
      [*] = ;                  var brupg : String = ParserGetValueByKeyByHandle(hcmd, brkey + 'upg');
      [*] = ;                  // resolve first, then check the nation actually has it:
      [*] = ;                  // _ai_TryUpgrade indexes gCountry[cid].upgrade[id] without any guard.
      [*] = ;                  var brupgc : Integer = -1;
      [*] = ;                  if brupg = 'century' then brupgc := gc_ai_upg_century
      [*] = ;                  else if brupg = 'food140' then brupgc := gc_ai_upg_food140
      [*] = ;                  else if brupg = 'horse' then brupgc := gc_ai_upg_horse
      [*] = ;                  else if brupg = 'fort' then brupgc := gc_ai_upg_fort
      [*] = ;                  else if brupg = 'reaper' then brupgc := gc_ai_upg_reaper
      [*] = ;                  else if brupg = 'stone200' then brupgc := gc_ai_upg_stone200
      [*] = ;                  else if brupg = 'stone100' then brupgc := gc_ai_upg_stone100
      [*] = ;                  else if brupg = 'builders' then brupgc := gc_ai_upg_builders
      [*] = ;                  else if brupg = 'wood' then brupgc := gc_ai_upg_wood
      [*] = ;                  else if brupg = 'feelds' then brupgc := gc_ai_upg_feelds
      [*] = ;                  else if brupg = 'bricks1' then brupgc := gc_ai_upg_bricks1
      [*] = ;                  else if brupg = 'bricks2' then brupgc := gc_ai_upg_bricks2
      [*] = ;                  else if brupg = 'horseswords' then brupgc := gc_ai_upg_horseswords
      [*] = ;                  else if brupg = 'armor1' then brupgc := gc_ai_upg_armor1
      [*] = ;                  else if brupg = 'newsteel' then brupgc := gc_ai_upg_newsteel;
      [*] = ;                  if (brupgc >= 0) then
      [*] = ;                  begin
      [*] = ;                     if (gPlayer[plind].aidata.upgradeid[brcid2][brupgc] >= 0) then
      [*] = ;                     _ai_TryUpgrade(plind, brcid2, brupgc);
      [*] = ;                  end;
      [*] = ;               end
      [*] = ;               else if brcmd = 'SET_RES' then
      [*] = ;                  _ai_SetResouceBalance(plind, brarg1, brarg2, -1, -1)
      [*] = ;               else if brcmd = 'MODE' then
      [*] = ;               begin
      [*] = ;                  // a1=1: build order comes from the model, native brain off.
      [*] = ;                  // bprogressEconomy is declared and saved by the engine but read
      [*] = ;                  // by nothing, so the bridge borrows it as the takeover switch.
      [*] = ;                  gPlayer[plind].aidata.bprogressEconomy := (brarg1 = 0);
      [*] = ;                  // a2=1: the model drives the waves, native attack is off.
      [*] = ;                  // Old command files carry no second argument: the parser
      [*] = ;                  // returns 0, so native war stays on and nothing changes.
      [*] = ;                  gPlayer[plind].aidata.bprogressWar := (brarg2 = 0);
      [*] = ;                  Log('bridge: native build order ' +
      [*] = ;                      BoolToStr(gPlayer[plind].aidata.bprogressEconomy) +
      [*] = ;                      ', native attack ' +
      [*] = ;                      BoolToStr(gPlayer[plind].aidata.bprogressWar) +
      [*] = ;                      ' for P' + IntToStr(plind));
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         DeleteFileStream(brcmdpath);
      [*] = ;         Log('bridge: applied ' + IntToStr(brcmdcount) + ' commands for P' + IntToStr(plind));
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;   // === END BRIDGE IMPORT ===