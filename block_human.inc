      [*] = ;   // === BRIDGE HUMAN PROBE: can a human slot be driven from here? ===
      [*] = ;   // Hackathon rules put the bot on a HUMAN slot, where the native AI never runs:
      [*] = ;   // progress.inc starts it one line above us and only for bai players or humans
      [*] = ;   // with the adviser on. This tick, however, runs for EVERY player.
      [*] = ;   // The probe answers what a rewrite needs to know, and nothing more:
      [*] = ;   //   1. does this tick really fire for a human slot;
      [*] = ;   //   2. can we read the world from here (gPlayer, objects, unit properties);
      [*] = ;   //   3. does _unit_GetCostByID work from here - the exact unit price the
      [*] = ;   //      AI side could never read. It IS in this build: lib/unit.script
      [*] = ;   //      declares procedure _unit_GetCostByID(const cid, unitID, plInd :
      [*] = ;   //      Integer; var food, wood, stone, gold, iron, coal : Integer).
      [*] = ;   //      An earlier note here claimed it was missing - that note came from
      [*] = ;   //      a grep that silently found nothing, and it was wrong.
      [*] = ;   // No orders are issued: a probe must not change the game it measures.
      [*] = ;   if (gPlayer[plind].bexists) and (not gPlayer[plind].bai) and
      [*] = ;      (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;   begin
      [*] = ;      var hprb : Integer = ParserSelectByKey('br_probe');
      [*] = ;      if (hprb = 0) then
      [*] = ;      hprb := ParserCreate('br_probe');
      [*] = ;      ParserClearByHandle(hprb);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'plind',    plind);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'tick',     gPlayer[plind].progresstick);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'gametime', Round(GetGameTime));
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'cid',      gPlayer[plind].cid);
      [*] = ;      ParserSetBoolValueByKeyByHandle(hprb, 'human',   gMap.players[plind].bhuman);
      [*] = ;      ParserSetBoolValueByKeyByHandle(hprb, 'adviser', gPlayer[plind].playeradviser.adviser.benable);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'food',  not gPlayer[plind].res[gc_resource_type_food]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'wood',  not gPlayer[plind].res[gc_resource_type_wood]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'stone', not gPlayer[plind].res[gc_resource_type_stone]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'gold',  not gPlayer[plind].res[gc_resource_type_gold]);
      [*] = ;      var hpph : Integer = GetPlayerHandleByIndex(plind);
      [*] = ;      var hpcount : Integer = GetPlayerGameObjectsCountByHandle(hpph);
      [*] = ;      var hppeas, hpbld, hpk : Integer;
      [*] = ;      var hpPeaCid : Integer = -1;
      [*] = ;      var hpPeaId : Integer = -1;
      [*] = ;      for hpk := 0 to hpcount-1 do
      [*] = ;      begin
      [*] = ;         var hpgo : Integer = GetGameObjectHandleByIndex(hpk, hpph);
      [*] = ;         var hppo : Pointer = _unit_GetTObj(hpgo);
      [*] = ;         if (hppo<>nil) then
      [*] = ;         begin
      [*] = ;            if (gObjProp[TObj(hppo).cid][TObj(hppo).id].usage = gc_obj_usage_peasant) then
      [*] = ;            begin
      [*] = ;               hppeas := hppeas + 1;
      [*] = ;               hpPeaCid := TObj(hppo).cid;
      [*] = ;               hpPeaId := TObj(hppo).id;
      [*] = ;            end;
      [*] = ;            if (gObjProp[TObj(hppo).cid][TObj(hppo).id].bbuilding) then
      [*] = ;            hpbld := hpbld + 1;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'objects',  hpcount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'peasants', hppeas);
      [*] = ;      ParserSetIntValueByKeyByHandle(hprb, 'bldgs',    hpbld);
      [*] = ;      if (hpPeaId >= 0) then
      [*] = ;      begin
      [*] = ;         var hpf, hpw, hps, hpg, hpi, hpc : Integer;
      [*] = ;         _unit_GetCostByID(hpPeaCid, hpPeaId, plind, hpf, hpw, hps, hpg, hpi, hpc);
      [*] = ;         ParserSetIntValueByKeyByHandle(hprb, 'pea_food',  hpf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hprb, 'pea_wood',  hpw);
      [*] = ;         ParserSetIntValueByKeyByHandle(hprb, 'pea_stone', hps);
      [*] = ;         ParserSetIntValueByKeyByHandle(hprb, 'pea_gold',  hpg);
      [*] = ;         ParserSetIntValueByKeyByHandle(hprb, 'pea_iron',  hpi);
      [*] = ;         ParserSetIntValueByKeyByHandle(hprb, 'pea_coal',  hpc);
      [*] = ;         ParserSetBoolValueByKeyByHandle(hprb, 'cost_ok', True);
      [*] = ;      end
      [*] = ;      else
      [*] = ;      ParserSetBoolValueByKeyByHandle(hprb, 'cost_ok', False);
      [*] = ;      ParserSaveToFileByHandle(hprb, '@@OUT@@coss3_probe_P' + IntToStr(plind) + '.dat');
      [*] = ;   end;
      [*] = ;   // === END BRIDGE HUMAN PROBE ===