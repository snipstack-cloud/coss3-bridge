      [*] = ;// === BRIDGE ATTACK: bot-ordered aggressor wave ===
      [*] = ;// Lives in the war-AI state: _ai_CreateAgressorArmy and friends are not
      [*] = ;// visible from progresseconomicai.inc - the two states have separate scopes.
      [*] = ;if (bai) and (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;begin
      [*] = ;   var bratkpath : String = '@@OUT@@coss3_atk_P' + IntToStr(plInd) + '.dat';
      [*] = ;   if IsFileExists(bratkpath) then
      [*] = ;   begin
      [*] = ;      var hatk : Integer = ParserSelectByKey('br_atk');
      [*] = ;      if (hatk = 0) then
      [*] = ;      hatk := ParserCreate('br_atk');
      [*] = ;      ParserClearByHandle(hatk);
      [*] = ;      var bratkcount : Integer;    // must live outside the block below
      [*] = ;      var bratktrg : String;       // what the model aims at
      [*] = ;      if ParserLoadFromFileByHandle(hatk, bratkpath) then
      [*] = ;      bratkcount := ParserGetIntValueByKeyByHandle(hatk, 'count');
      [*] = ;      bratktrg := ParserGetValueByKeyByHandle(hatk, 'target');
      [*] = ;      DeleteFileStream(bratkpath);
      [*] = ;      if (bratkcount > 0) and (not gbool_peacemode) then
      [*] = ;      begin
      [*] = ;         // The native AI arms this only once per match (agressorsSent = 0);
      [*] = ;         // clearing it lets the bot send wave after wave.
      [*] = ;         gPlayer[plInd].aiData.agressorsSent := 0;
      [*] = ;         // FRESH TROOPS FIRST. Taking from .agressors pulls units out of a
      [*] = ;         // wave that is already marching: it regroups and stalls near the
      [*] = ;         // base. That is why every repeat order used to be refused by the
      [*] = ;         // python side. With freewarriors first a new wave is built from
      [*] = ;         // troops that are not marching anywhere, and waves can follow
      [*] = ;         // one another.
      [*] = ;         var pBrArmy : Pointer = _ai_CreateAgressorArmy(plInd, bratkcount, gPlayer[plInd].aiData.freewarriors);
      [*] = ;         if (pBrArmy = nil) then
      [*] = ;         pBrArmy := _ai_CreateAgressorArmy(plInd, bratkcount, gPlayer[plInd].aiData.agressors);
      [*] = ;         if (pBrArmy <> nil) then
      [*] = ;         begin
      [*] = ;            _ai_ArmyMakeAgressorBattle(pBrArmy);
      [*] = ;            // THE MODEL PICKS THE TARGET. Left alone, _ai_ArmyAgressorLink aims at
      [*] = ;            // enemy ARMIES and, failing that, at visible units or UNFINISHED
      [*] = ;            // buildings - a finished quiet base is no target at all, so the wave
      [*] = ;            // finds nothing and mills around at home (seen 11.09.2026).
      [*] = ;            //   target=peasants - enemy peasant nearest to our base: the objective
      [*] = ;            //   target=base     - first building of the first enemy
      [*] = ;            //   target=army     - hand the choice back to the engine
      [*] = ;            var brTrgHnd : Integer;
      [*] = ;            var brTrgX, brTrgZ : Float;
      [*] = ;            var brBest : Float = 1000000;
      [*] = ;            var brI, brK : Integer;
      [*] = ;            if (bratktrg <> 'army') then
      [*] = ;            for brI := 0 to gc_MaxPlayerCount-1 do
      [*] = ;            if gPlayer[brI].bExists and
      [*] = ;               ((gPlayer[plInd].enemyPlMask and gPlayer[brI].myPlMask) <> 0) then
      [*] = ;            begin
      [*] = ;               if (bratktrg = 'peasants') then
      [*] = ;               begin
      [*] = ;                  var brPh : Integer = GetPlayerHandleByIndex(brI);
      [*] = ;                  var brCnt : Integer = GetPlayerGameObjectsCountByHandle(brPh);
      [*] = ;                  for brK := 0 to brCnt-1 do
      [*] = ;                  begin
      [*] = ;                     var brGo : Integer = GetGameObjectHandleByIndex(brK, brPh);
      [*] = ;                     var brPo : Pointer = _unit_GetTObj(brGo);
      [*] = ;                     if (brPo<>nil) then
      [*] = ;                     if (gObjProp[TObj(brPo).cid][TObj(brPo).id].usage = gc_obj_usage_peasant) then
      [*] = ;                     begin
      [*] = ;                        var brX : Float = GetGameObjectPositionXByHandle(brGo);
      [*] = ;                        var brZ : Float = GetGameObjectPositionZByHandle(brGo);
      [*] = ;                        var brD : Float = VectorDistance(brX, 0, brZ,
      [*] = ;                             gPlayer[plInd].aiData.centerX, 0, gPlayer[plInd].aiData.centerZ);
      [*] = ;                        if (brD < brBest) then
      [*] = ;                        begin
      [*] = ;                           brBest := brD;
      [*] = ;                           brTrgHnd := brGo;
      [*] = ;                           brTrgX := brX;
      [*] = ;                           brTrgZ := brZ;
      [*] = ;                        end;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end
      [*] = ;               else
      [*] = ;               if (brTrgHnd = 0) and (gPlayer[brI].lists.buildings.GetCount > 0) then
      [*] = ;               begin
      [*] = ;                  brTrgHnd := gPlayer[brI].lists.buildings.Get(0);
      [*] = ;                  brTrgX := GetGameObjectPositionXByHandle(brTrgHnd);
      [*] = ;                  brTrgZ := GetGameObjectPositionZByHandle(brTrgHnd);
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;            if (brTrgHnd <> 0) then
      [*] = ;            begin
      [*] = ;               _ai_SetArmyPosition(pBrArmy, brTrgX, brTrgZ, 0, 0, gc_obj_order_move_mode_attack);
      [*] = ;               Log('bridge: wave of ' + IntToStr(bratkcount) + ' target=' + bratktrg +
      [*] = ;                   ' at ' + FloatToStr(brTrgX) + ',' + FloatToStr(brTrgZ) +
      [*] = ;                   ' for P' + IntToStr(plInd));
      [*] = ;            end
      [*] = ;            else
      [*] = ;            Log('bridge: wave of ' + IntToStr(bratkcount) + ' target=' + bratktrg +
      [*] = ;                ' NOT FOUND for P' + IntToStr(plInd) + ' - engine picks the target');
      [*] = ;         end
      [*] = ;         else
      [*] = ;         Log('bridge: attack refused, not enough free warriors for P' + IntToStr(plInd));
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;end;
      [*] = ;// === END BRIDGE ATTACK ===
