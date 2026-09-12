      [*] = ;// === BRIDGE STATE: written every AI tick, unconditional (v2: + map intel) ===
      [*] = ;// Placed before the centerfound check on purpose: this spot is proven safe.
      [*] = ;if (not _net_IsClient) and (not _net_IsReplay) then
      [*] = ;begin
      [*] = ;   var hbp : Integer = ParserSelectByKey('br_state');
      [*] = ;   if (hbp = 0) then
      [*] = ;   hbp := ParserCreate('br_state');
      [*] = ;   ParserClearByHandle(hbp);
      [*] = ;   var brcid : Integer = gPlayer[plind].cid;
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'plind',       plind);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'cid',         brcid);
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'bai',         bai);
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'centerfound', gPlayer[plind].aidata.centerfound);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'gametime',    Round(GetGameTime));
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'peacemode',   gbool_peacemode);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'peacetime_end',Round(gfloat_peacetime));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'food',        not gPlayer[plind].res[gc_resource_type_food]);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'wood',        not gPlayer[plind].res[gc_resource_type_wood]);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'stone',       not gPlayer[plind].res[gc_resource_type_stone]);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'gold',        not gPlayer[plind].res[gc_resource_type_gold]);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'iron',        not gPlayer[plind].res[gc_resource_type_iron]);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'coal',        not gPlayer[plind].res[gc_resource_type_coal]);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'peasants',    _ai_GetUnitCount(plind, brcid, gc_ai_unit_peasant));
      [*] = ;   // Что ратуша и казарма ДЕЛАЮТ прямо сейчас. Без этого «найм не растёт»
      [*] = ;   // неотличимо от «заказ не принят»: 11.09.2026 крестьяне стояли на 22
      [*] = ;   // десять тактов при полных ресурсах, и причину было не увидеть.
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'inprod_pea',  _ai_GetUnitCountInProduce(plind, brcid, gPlayer[plind].aidata.aiunit[brcid][gc_ai_unit_peasant]));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'inprod_inf',  _ai_GetUnitCountInProduce(plind, brcid, gPlayer[plind].aidata.aiunit[brcid][gc_ai_unit_infantry17]));
      [*] = ;   // Ответ САМОГО движка на вопрос «почему не нанимается». _ai_TryUnit
      [*] = ;   // пускает наш TRAIN только если _unit_CanApplyCountCostByID сказала
      [*] = ;   // «хватает», а она живёт в бинарнике: цены юнитов иначе не узнать.
      [*] = ;   // bfamine - флаг голода, из-за него движок сам гонит людей на еду.
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'can_pea', _unit_CanApplyCountCostByID(brcid, gPlayer[plind].aidata.aiunit[brcid][gc_ai_unit_peasant], plind, 1));
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'can_inf', _unit_CanApplyCountCostByID(brcid, gPlayer[plind].aidata.aiunit[brcid][gc_ai_unit_infantry17], plind, 1));
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'famine',  gPlayer[plind].bfamine);
      [*] = ;   // Сколько крестьян забрали стройки: сумма npeasantscalled по живым
      [*] = ;   // проектам. Без этого числа не видно, кто съел добычу.
      [*] = ;   var bmbuild : Integer;
      [*] = ;   var bmbi : Integer;
      [*] = ;   for bmbi := 0 to gc_ai_max_construction_sites-1 do
      [*] = ;   if (gPlayer[plind].aidata.buildprojects[bmbi].used) then
      [*] = ;   bmbuild := bmbuild + gPlayer[plind].aidata.buildprojects[bmbi].npeasantscalled;
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'on_build', bmbuild);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'centers',     _ai_GetUnitCount(plind, brcid, gc_ai_unit_center));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'mills',       _ai_GetUnitCount(plind, brcid, gc_ai_unit_mill));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'ba17',        _ai_GetUnitCount(plind, brcid, gc_ai_unit_ba17));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'ba18',        _ai_GetUnitCount(plind, brcid, gc_ai_unit_ba18));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'stables',     _ai_GetUnitCount(plind, brcid, gc_ai_unit_stable));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'smiths',      _ai_GetUnitCount(plind, brcid, gc_ai_unit_smith));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'academies',   _ai_GetUnitCount(plind, brcid, gc_ai_unit_academi));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'markets',     _ai_GetUnitCount(plind, brcid, gc_ai_unit_market));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'houses',      _ai_GetUnitCount(plind, brcid, gc_ai_unit_house));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'mines_gold',  _ai_GetUnitCount(plind, brcid, gc_ai_unit_minegold));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'mines_iron',  _ai_GetUnitCount(plind, brcid, gc_ai_unit_mineiron));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'mines_coal',  _ai_GetUnitCount(plind, brcid, gc_ai_unit_minecoal));
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'on_food',  gPlayer[plind].aidata.onFood);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'on_wood',  gPlayer[plind].aidata.onWood);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'on_stone', gPlayer[plind].aidata.onStone);
      [*] = ;   // upgradeid[] is -1 when the nation lacks the upgrade -> upgstate[cid][-1] crashes
      [*] = ;   var brupgid : Integer;
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_century];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_century', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_century', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_food140];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_food140', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_food140', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_horse];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_horse', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_horse', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_fort];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_fort', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_fort', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_reaper];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_reaper', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_reaper', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_stone200];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_stone200', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_stone200', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_builders];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_builders', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_builders', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_wood];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_wood', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_wood', False);
      [*] = ;   brupgid := gPlayer[plind].aidata.upgradeid[brcid][gc_ai_upg_feelds];
      [*] = ;   if (brupgid >= 0) then
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_feelds', gPlayer[plind].upgstate[brcid][brupgid].done)
      [*] = ;   else
      [*] = ;   ParserSetBoolValueByKeyByHandle(hbp, 'upg_feelds', False);
      [*] = ;   var brslots : Integer;
      [*] = ;   var brj : Integer;
      [*] = ;   for brj := 0 to gc_ai_max_construction_sites-1 do
      [*] = ;   if gPlayer[plind].aidata.buildprojects[brj].used then
      [*] = ;   brslots := brslots + 1;
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'build_slots_used',  brslots);
      [*] = ;   ParserSetIntValueByKeyByHandle(hbp, 'build_slots_total', gc_ai_max_construction_sites);
      [*] = ;
      [*] = ;   // --- map intelligence: AI players only, and only once the base is known ---
      [*] = ;   if (bai) and (gPlayer[plind].aidata.centerfound) then
      [*] = ;   begin
      [*] = ;      const cBmGrid = 16;
      [*] = ;      var bmx : Float = gPlayer[plind].aidata.centerx;
      [*] = ;      var bmz : Float = gPlayer[plind].aidata.centerz;
      [*] = ;      var bmmapw : Integer = GetMapWidth;
      [*] = ;      var bmmaph : Integer = GetMapHeight;
      [*] = ;      var bmhalfw : Integer = bmmapw div 2;
      [*] = ;      var bmhalfh : Integer = bmmaph div 2;
      [*] = ;      var bmi, bmj, bmk : Integer;
      [*] = ;      // world x in [-map_w/2 .. map_w/2] -> column 0..grid_n-1, z the same for rows
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'map_w',  bmmapw);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'map_h',  bmmaph);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'grid_n', cBmGrid);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_x',   Round(bmx));
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_z',   Round(bmz));
      [*] = ;      var bmcx : Integer = floor((bmx+bmhalfw)*cBmGrid/bmmapw);
      [*] = ;      var bmcy : Integer = floor((bmz+bmhalfh)*cBmGrid/bmmaph);
      [*] = ;      if (bmcx<0) then bmcx := 0;
      [*] = ;      if (bmcx>cBmGrid-1) then bmcx := cBmGrid-1;
      [*] = ;      if (bmcy<0) then bmcy := 0;
      [*] = ;      if (bmcy>cBmGrid-1) then bmcy := cBmGrid-1;
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_cx', bmcx);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_cy', bmcy);
      [*] = ;      var bmzone : Integer = TopologyGetZoneIndex(bmx, bmz);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_zone',     bmzone);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'zones_total', TopologyGetZonesCount);
      [*] = ;
      [*] = ;      // cumulative gathered amounts; the client turns deltas into a real rate.
      [*] = ;      // stat.restotal is a plain counter - unlike res[], it is NOT inverted.
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'tot_food',  gPlayer[plind].stat.restotal[gc_resource_type_food]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'tot_wood',  gPlayer[plind].stat.restotal[gc_resource_type_wood]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'tot_stone', gPlayer[plind].stat.restotal[gc_resource_type_stone]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'tot_gold',  gPlayer[plind].stat.restotal[gc_resource_type_gold]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'tot_iron',  gPlayer[plind].stat.restotal[gc_resource_type_iron]);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'tot_coal',  gPlayer[plind].stat.restotal[gc_resource_type_coal]);
      [*] = ;
      [*] = ;      // ore deposits: orelist is filled at init and sorted by distance to the center
      [*] = ;      var bmgoldd : Integer = -1;
      [*] = ;      var bmirond : Integer = -1;
      [*] = ;      var bmcoald : Integer = -1;
      [*] = ;      var bmgoldn, bmironn, bmcoaln : Integer;
      [*] = ;      for bmk := 0 to gPlayer[plind].aidata.orelist.GetCount-1 do
      [*] = ;      begin
      [*] = ;         var bmoreh : Integer = gPlayer[plind].aidata.orelist.Get(bmk);
      [*] = ;         var bmpres : Pointer = _res_GetTRes(bmoreh);
      [*] = ;         if (bmpres<>nil) then
      [*] = ;         begin
      [*] = ;            var bmox : Float = GetGameObjectPositionXByHandle(bmoreh);
      [*] = ;            var bmoz : Float = GetGameObjectPositionZByHandle(bmoreh);
      [*] = ;            var bmod : Integer = Round(VectorDistance(bmox, 0, bmoz, bmx, 0, bmz));
      [*] = ;            var bmnear : Boolean = (bmod<gc_ai_dist_mines_expansion);
      [*] = ;            case TRes(bmpres).itype of
      [*] = ;               gc_resource_type_gold :
      [*] = ;               begin
      [*] = ;                  if (bmgoldd<0) then bmgoldd := bmod;
      [*] = ;                  if (bmnear) then bmgoldn := bmgoldn + 1;
      [*] = ;               end;
      [*] = ;               gc_resource_type_iron :
      [*] = ;               begin
      [*] = ;                  if (bmirond<0) then bmirond := bmod;
      [*] = ;                  if (bmnear) then bmironn := bmironn + 1;
      [*] = ;               end;
      [*] = ;               gc_resource_type_coal :
      [*] = ;               begin
      [*] = ;                  if (bmcoald<0) then bmcoald := bmod;
      [*] = ;                  if (bmnear) then bmcoaln := bmcoaln + 1;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'ore_gold_dist', bmgoldd);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'ore_iron_dist', bmirond);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'ore_coal_dist', bmcoald);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'ore_gold_near', bmgoldn);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'ore_iron_near', bmironn);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'ore_coal_near', bmcoaln);
      [*] = ;
      [*] = ;      // my own holdings and forces
      [*] = ;      // TPlayer.unitcount is never filled by anything - count owned objects instead
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_objects',  GetPlayerGameObjectsCountByHandle(GetPlayerHandleByIndex(plind)));
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_buildings', gPlayer[plind].lists.buildings.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_stores',    gPlayer[plind].aidata.storelist.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_towers',    gPlayer[plind].aidata.towers.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_armies',    gPlayer[plind].aidata.armylist.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_defenders', gPlayer[plind].aidata.defenders.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_guards',    gPlayer[plind].aidata.guards.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_agressors', gPlayer[plind].aidata.agressors.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_freewar',   gPlayer[plind].aidata.freewarriors.GetCount);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_damaged',   gPlayer[plind].aidata.damagedBuildings.GetCount);
      [*] = ;      // Жилые места: сколько дают здания и сколько занято. Нативный ИИ
      [*] = ;      // строит дома, когда запас меньше 20 (progresseconomicai.inc:2861).
      [*] = ;      // Настройка карты может урезать предел ниже, чем даёт farm.
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_farm',      gPlayer[plind].farm);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_farmused',  gPlayer[plind].counter.farmused);
      [*] = ;      var bmmilinf : Integer = _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_infantry17) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_uniq_inf17) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_uniq_inf18) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_pikeman18) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_grenadier);
      [*] = ;      var bmmilsh : Integer = _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_musk17) +
      [*] = ;                              _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_musk18) +
      [*] = ;                              _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_archer);
      [*] = ;      var bmmilcav : Integer = _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_hussar) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_cuirassier) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_dragoon17) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_dragun18) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_reitar) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_uniq_cav17) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_uniq_cav18);
      [*] = ;      var bmmilart : Integer = _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_cannon) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_howitzer) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_mortar) +
      [*] = ;                               _ai_GetUnitCountAnyFaction(plind, gc_ai_unit_mbarrel);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'mil_inf',      bmmilinf);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'mil_shooters', bmmilsh);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'mil_cav',      bmmilcav);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'mil_art',      bmmilart);
      [*] = ;
      [*] = ;      // who else is on this map
      [*] = ;      var bmenmask : Integer = gPlayer[plind].enemyplmask;
      [*] = ;      var bmplcount : Integer;
      [*] = ;      var bmpl : Integer;
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'my_team', gPlayer[plind].team);
      [*] = ;      for bmpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;      if (gPlayer[bmpl].bexists) then
      [*] = ;      begin
      [*] = ;         bmplcount := bmplcount + 1;
      [*] = ;         var bmpfx : String = 'p' + IntToStr(bmpl) + '_';
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmpfx+'team',   gPlayer[bmpl].team);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmpfx+'cid',    gPlayer[bmpl].cid);
      [*] = ;         ParserSetBoolValueByKeyByHandle(hbp, bmpfx+'ai',    gPlayer[bmpl].bai);
      [*] = ;         ParserSetBoolValueByKeyByHandle(hbp, bmpfx+'enemy', ((bmenmask and (1 shl bmpl))<>0));
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmpfx+'objects', GetPlayerGameObjectsCountByHandle(GetPlayerHandleByIndex(bmpl)));
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmpfx+'bldgs',  gPlayer[bmpl].lists.buildings.GetCount);
      [*] = ;      end;
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'players', bmplcount);
      [*] = ;
      [*] = ;      // danger / attractiveness of the home zone (native war-AI potential field)
      [*] = ;      var bmdanger, bmattract : Integer;
      [*] = ;      if (bmzone>=0) then
      [*] = ;      begin
      [*] = ;         var bmpzone : Pointer = TopologyGetZoneBufferByIndex(bmzone);
      [*] = ;         if (bmpzone<>nil) then
      [*] = ;         begin
      [*] = ;            bmdanger  := Round(TTopZone(bmpzone).danger[plind]);
      [*] = ;            bmattract := Round(TTopZone(bmpzone).attract[plind]);
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'danger_home',  bmdanger);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'attract_home', bmattract);
      [*] = ;      var bmlastatk : Integer = -1;
      [*] = ;      if (gPlayer[plind].lastattacktime>0) then
      [*] = ;      bmlastatk := Round(GetGameTime-gPlayer[plind].lastattacktime);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'last_attack_ago', bmlastatk);
      [*] = ;
      [*] = ;      // minimap layer 1: bases.  0 empty, 1 ally, 2 mine, 3 enemy, 4 my town center
      [*] = ;      // minimap layer 2: enemy army strength per cell
      [*] = ;      var bmbase : array [0..15] of array [0..15] of Integer;
      [*] = ;      var bmforce : array [0..15] of array [0..15] of Integer;
      [*] = ;      for bmi := 0 to cBmGrid-1 do
      [*] = ;      for bmj := 0 to cBmGrid-1 do
      [*] = ;      begin
      [*] = ;         bmbase[bmi][bmj] := 0;
      [*] = ;         bmforce[bmi][bmj] := 0;
      [*] = ;      end;
      [*] = ;      for bmpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;      if (gPlayer[bmpl].bexists) then
      [*] = ;      begin
      [*] = ;         var bmcode : Integer = 1;
      [*] = ;         if (bmpl=plind) then
      [*] = ;         bmcode := 2
      [*] = ;         else
      [*] = ;         if ((bmenmask and (1 shl bmpl))<>0) then
      [*] = ;         bmcode := 3;
      [*] = ;         for bmk := 0 to gPlayer[bmpl].lists.buildings.GetCount-1 do
      [*] = ;         begin
      [*] = ;            var bmbh : Integer = gPlayer[bmpl].lists.buildings.Get(bmk);
      [*] = ;            var bmbx : Float = GetGameObjectPositionXByHandle(bmbh);
      [*] = ;            var bmbz : Float = GetGameObjectPositionZByHandle(bmbh);
      [*] = ;            var bmbcx : Integer = floor((bmbx+bmhalfw)*cBmGrid/bmmapw);
      [*] = ;            var bmbcy : Integer = floor((bmbz+bmhalfh)*cBmGrid/bmmaph);
      [*] = ;            if (bmbcx>=0) and (bmbcx<cBmGrid) and (bmbcy>=0) and (bmbcy<cBmGrid) then
      [*] = ;            if (bmbase[bmbcx][bmbcy]<bmcode) then
      [*] = ;            bmbase[bmbcx][bmbcy] := bmcode;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      bmbase[bmcx][bmcy] := 4;
      [*] = ;
      [*] = ;      // enemy armies, exactly as the native war AI sees them
      [*] = ;      var bmenarm, bmenforce, bmenmax, bmentow : Integer;
      [*] = ;      var bmneard : Integer = -1;
      [*] = ;      var bmnearf, bmneari, bmnears, bmnearc, bmnearg : Integer;
      [*] = ;      var bmtopd : array [0..3] of Integer;
      [*] = ;      var bmtopf : array [0..3] of Integer;
      [*] = ;      var bmtopi : array [0..3] of Integer;
      [*] = ;      var bmtops : array [0..3] of Integer;
      [*] = ;      var bmtopc : array [0..3] of Integer;
      [*] = ;      var bmtopg : array [0..3] of Integer;
      [*] = ;      var bmtopx : array [0..3] of Integer;
      [*] = ;      var bmtopy : array [0..3] of Integer;
      [*] = ;      for bmi := 0 to 3 do
      [*] = ;      bmtopd[bmi] := -1;
      [*] = ;      var bmpen : Pointer = _misc_GetPlayerEnemyInfo(plind);
      [*] = ;      if (bmpen<>nil) then
      [*] = ;      begin
      [*] = ;         bmentow := TEnemyInfo(bmpen).towers.GetCount;
      [*] = ;         for bmk := 0 to TEnemyInfo(bmpen).armyInfos.GetCount-1 do
      [*] = ;         begin
      [*] = ;            var bmpai : Pointer = TEnemyInfo(bmpen).armyInfos.Get(bmk);
      [*] = ;            if (TArmyInfo(bmpai).landCount>0) then
      [*] = ;            begin
      [*] = ;               bmenarm := bmenarm + 1;
      [*] = ;               bmenforce := bmenforce + TArmyInfo(bmpai).force;
      [*] = ;               if (TArmyInfo(bmpai).force>bmenmax) then
      [*] = ;               bmenmax := TArmyInfo(bmpai).force;
      [*] = ;               var bmsgx : Float = (TArmyInfo(bmpai).minX+TArmyInfo(bmpai).maxX)/2;
      [*] = ;               var bmsgy : Float = (TArmyInfo(bmpai).minY+TArmyInfo(bmpai).maxY)/2;
      [*] = ;               var bmax, bmay : Float;
      [*] = ;               _misc_ScanGridIndicesToPos(bmsgx, bmsgy, bmax, bmay);
      [*] = ;               var bmad : Integer = Round(VectorDistance(bmax, 0, bmay, bmx, 0, bmz));
      [*] = ;               var bmacx : Integer = floor((bmax+bmhalfw)*cBmGrid/bmmapw);
      [*] = ;               var bmacy : Integer = floor((bmay+bmhalfh)*cBmGrid/bmmaph);
      [*] = ;               if (bmacx>=0) and (bmacx<cBmGrid) and (bmacy>=0) and (bmacy<cBmGrid) then
      [*] = ;               bmforce[bmacx][bmacy] := bmforce[bmacx][bmacy] + TArmyInfo(bmpai).force;
      [*] = ;               var bmguns : Integer = TArmyInfo(bmpai).cannons+TArmyInfo(bmpai).mortars+TArmyInfo(bmpai).mcannons;
      [*] = ;               if (bmneard<0) or (bmad<bmneard) then
      [*] = ;               begin
      [*] = ;                  bmneard := bmad;
      [*] = ;                  bmnearf := TArmyInfo(bmpai).force;
      [*] = ;                  bmneari := TArmyInfo(bmpai).infantry;
      [*] = ;                  bmnears := TArmyInfo(bmpai).shooters;
      [*] = ;                  bmnearc := TArmyInfo(bmpai).cavalry;
      [*] = ;                  bmnearg := bmguns;
      [*] = ;               end;
      [*] = ;               // keep the four strongest armies, sorted by force
      [*] = ;               for bmi := 0 to 3 do
      [*] = ;               if (TArmyInfo(bmpai).force>bmtopf[bmi]) or (bmtopd[bmi]<0) then
      [*] = ;               begin
      [*] = ;                  for bmj := 3 downto bmi+1 do
      [*] = ;                  begin
      [*] = ;                     bmtopd[bmj] := bmtopd[bmj-1];
      [*] = ;                     bmtopf[bmj] := bmtopf[bmj-1];
      [*] = ;                     bmtopi[bmj] := bmtopi[bmj-1];
      [*] = ;                     bmtops[bmj] := bmtops[bmj-1];
      [*] = ;                     bmtopc[bmj] := bmtopc[bmj-1];
      [*] = ;                     bmtopg[bmj] := bmtopg[bmj-1];
      [*] = ;                     bmtopx[bmj] := bmtopx[bmj-1];
      [*] = ;                     bmtopy[bmj] := bmtopy[bmj-1];
      [*] = ;                  end;
      [*] = ;                  bmtopd[bmi] := bmad;
      [*] = ;                  bmtopf[bmi] := TArmyInfo(bmpai).force;
      [*] = ;                  bmtopi[bmi] := TArmyInfo(bmpai).infantry;
      [*] = ;                  bmtops[bmi] := TArmyInfo(bmpai).shooters;
      [*] = ;                  bmtopc[bmi] := TArmyInfo(bmpai).cavalry;
      [*] = ;                  bmtopg[bmi] := bmguns;
      [*] = ;                  bmtopx[bmi] := bmacx;
      [*] = ;                  bmtopy[bmi] := bmacy;
      [*] = ;                  break;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;      end;
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_armies',      bmenarm);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_force_total', bmenforce);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_force_max',   bmenmax);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_towers',      bmentow);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_near_dist',   bmneard);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_near_force',  bmnearf);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_near_inf',    bmneari);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_near_sh',     bmnears);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_near_cav',    bmnearc);
      [*] = ;      ParserSetIntValueByKeyByHandle(hbp, 'en_near_guns',   bmnearg);
      [*] = ;      for bmi := 0 to 3 do
      [*] = ;      if (bmtopd[bmi]>=0) then
      [*] = ;      begin
      [*] = ;         var bmapfx : String = 'a' + IntToStr(bmi) + '_';
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'dist',  bmtopd[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'force', bmtopf[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'inf',   bmtopi[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'sh',    bmtops[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'cav',   bmtopc[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'guns',  bmtopg[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'cx',    bmtopx[bmi]);
      [*] = ;         ParserSetIntValueByKeyByHandle(hbp, bmapfx+'cy',    bmtopy[bmi]);
      [*] = ;      end;
      [*] = ;
      [*] = ;      var bmrow : String;
      [*] = ;      for bmj := 0 to cBmGrid-1 do
      [*] = ;      begin
      [*] = ;         bmrow := '';
      [*] = ;         for bmi := 0 to cBmGrid-1 do
      [*] = ;         begin
      [*] = ;            case bmbase[bmi][bmj] of
      [*] = ;               1 : bmrow := bmrow + 'a';
      [*] = ;               2 : bmrow := bmrow + 'b';
      [*] = ;               3 : bmrow := bmrow + 'e';
      [*] = ;               4 : bmrow := bmrow + 'H'
      [*] = ;               else
      [*] = ;               bmrow := bmrow + '.';
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetValueByKeyByHandle(hbp, 'brow'+IntToStr(bmj), bmrow);
      [*] = ;      end;
      [*] = ;      for bmj := 0 to cBmGrid-1 do
      [*] = ;      begin
      [*] = ;         bmrow := '';
      [*] = ;         for bmi := 0 to cBmGrid-1 do
      [*] = ;         begin
      [*] = ;            var bmfv : Integer = bmforce[bmi][bmj] div 50;
      [*] = ;            if (bmfv>9) then bmfv := 9;
      [*] = ;            if (bmforce[bmi][bmj]>0) and (bmfv<1) then bmfv := 1;
      [*] = ;            if (bmfv>0) then
      [*] = ;            bmrow := bmrow + IntToStr(bmfv)
      [*] = ;            else
      [*] = ;            bmrow := bmrow + '.';
      [*] = ;         end;
      [*] = ;         ParserSetValueByKeyByHandle(hbp, 'frow'+IntToStr(bmj), bmrow);
      [*] = ;      end;
      [*] = ;
      [*] = ;      // --- terrain layer: a full resource-grid sweep, so rebuild at most every 20 s.
      [*] = ;      // The named parser survives between ticks, so its own gametime is the timer -
      [*] = ;      // no extra global and no second patched file.
      [*] = ;      var bmmapkey : String = 'br_map_P' + IntToStr(plind);
      [*] = ;      var bmlast : Integer = -1000;
      [*] = ;      var hmp : Integer = ParserSelectByKey(bmmapkey);
      [*] = ;      if (hmp = 0) then
      [*] = ;      hmp := ParserCreate(bmmapkey)
      [*] = ;      else
      [*] = ;      bmlast := ParserGetIntValueByKeyByHandle(hmp, 'gametime');
      [*] = ;      if ((Round(GetGameTime)-bmlast)>=20) or (Round(GetGameTime)<bmlast) then
      [*] = ;      begin
      [*] = ;         ParserClearByHandle(hmp);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'gametime', Round(GetGameTime));
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'plind',  plind);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'grid_n', cBmGrid);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'map_w',  bmmapw);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'map_h',  bmmaph);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'cell_w', bmmapw div cBmGrid);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'cell_h', bmmaph div cBmGrid);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'my_cx',  bmcx);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'my_cy',  bmcy);
      [*] = ;
      [*] = ;         var bmres : array [0..15] of array [0..15] of Integer;
      [*] = ;         var bmwood : array [0..15] of array [0..15] of Integer;
      [*] = ;         for bmi := 0 to cBmGrid-1 do
      [*] = ;         for bmj := 0 to cBmGrid-1 do
      [*] = ;         begin
      [*] = ;            bmres[bmi][bmj] := 0;
      [*] = ;            bmwood[bmi][bmj] := 0;
      [*] = ;         end;
      [*] = ;         var bmgridx : Integer = floor(bmx+bmhalfw) div gc_resgrid_size;
      [*] = ;         var bmgridy : Integer = floor(bmz+bmhalfh) div gc_resgrid_size;
      [*] = ;         var bmwn, bmwf, bmsn, bmsf : Integer;
      [*] = ;         var bmwdist : Integer = -1;
      [*] = ;         var bmgx, bmgy : Integer;
      [*] = ;         for bmgx := 0 to gc_resgrid_countx-1 do
      [*] = ;         for bmgy := 0 to gc_resgrid_county-1 do
      [*] = ;         begin
      [*] = ;            var bmwc : Integer = gResGrid[bmgx,bmgy].fResCount[gc_resource_type_wood];
      [*] = ;            var bmsc : Integer = gResGrid[bmgx,bmgy].fResCount[gc_resource_type_stone];
      [*] = ;            if ((bmwc+bmsc)>0) then
      [*] = ;            begin
      [*] = ;               var bmpx : Float = bmgx*gc_resgrid_size-bmhalfw;
      [*] = ;               var bmpz : Float = bmgy*gc_resgrid_size-bmhalfh;
      [*] = ;               var bmrcx : Integer = floor((bmpx+bmhalfw)*cBmGrid/bmmapw);
      [*] = ;               var bmrcy : Integer = floor((bmpz+bmhalfh)*cBmGrid/bmmaph);
      [*] = ;               if (bmrcx>=0) and (bmrcx<cBmGrid) and (bmrcy>=0) and (bmrcy<cBmGrid) then
      [*] = ;               begin
      [*] = ;                  bmwood[bmrcx][bmrcy] := bmwood[bmrcx][bmrcy] + bmwc;
      [*] = ;                  if (bmsc>bmwc) and (bmres[bmrcx][bmrcy]<1) then
      [*] = ;                  bmres[bmrcx][bmrcy] := 1;
      [*] = ;               end;
      [*] = ;               var bmcd : Integer = Round(Sqrt(Sqr(bmgridx-bmgx)+Sqr(bmgridy-bmgy)));
      [*] = ;               if (bmcd<=10) then
      [*] = ;               begin
      [*] = ;                  bmwn := bmwn + bmwc*gc_gameplay_resource_maxattackers_wood;
      [*] = ;                  bmsn := bmsn + bmsc*gc_gameplay_resource_maxattackers_stone;
      [*] = ;                  bmwf := bmwf + Max(0, bmwc*gc_gameplay_resource_maxattackers_wood-gResGrid[bmgx,bmgy].fWorkerCount[plind][gc_resource_type_wood]);
      [*] = ;                  bmsf := bmsf + Max(0, bmsc*gc_gameplay_resource_maxattackers_stone-gResGrid[bmgx,bmgy].fWorkerCount[plind][gc_resource_type_stone]);
      [*] = ;               end;
      [*] = ;               if (bmwc>0) and ((bmwdist<0) or (bmcd<bmwdist)) then
      [*] = ;               bmwdist := bmcd;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'wood_slots_near',  bmwn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'wood_slots_free',  bmwf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'stone_slots_near', bmsn);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'stone_slots_free', bmsf);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'wood_dist_cells',  bmwdist);
      [*] = ;
      [*] = ;         // free deposits: no building standing on them, reachable from my island
      [*] = ;         var bmfg, bmfi, bmfc, bmlisted : Integer;
      [*] = ;         for bmk := 0 to gPlayer[plind].aidata.orelist.GetCount-1 do
      [*] = ;         begin
      [*] = ;            var bmoreh : Integer = gPlayer[plind].aidata.orelist.Get(bmk);
      [*] = ;            var bmpres : Pointer = _res_GetTRes(bmoreh);
      [*] = ;            if (bmpres<>nil) then
      [*] = ;            begin
      [*] = ;               var bmox : Float = GetGameObjectPositionXByHandle(bmoreh);
      [*] = ;               var bmoz : Float = GetGameObjectPositionZByHandle(bmoreh);
      [*] = ;               var bmfree : Boolean = _misc_IsCorrectIslandPosition(plind, bmox, bmoz);
      [*] = ;               if (bmfree) then
      [*] = ;               begin
      [*] = ;                  _misc_MakeListObjectsInRadius(bmox, bmoz, 1, false, (1 shl gc_obj_material_building), 0, True, gIntegerList);
      [*] = ;                  for bmj := gIntegerList.GetCount-1 downto 0 do
      [*] = ;                  begin
      [*] = ;                     var bmbh : Integer = gIntegerList.Get(bmj);
      [*] = ;                     var bmbx : Float = GetGameObjectPositionXByHandle(bmbh);
      [*] = ;                     var bmbz : Float = GetGameObjectPositionZByHandle(bmbh);
      [*] = ;                     if (VectorDistance(bmox, 0, bmoz, bmbx, 0, bmbz)<gc_epsilon+0.5) then
      [*] = ;                     begin
      [*] = ;                        bmfree := false;
      [*] = ;                        break;
      [*] = ;                     end;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               var bmocx : Integer = floor((bmox+bmhalfw)*cBmGrid/bmmapw);
      [*] = ;               var bmocy : Integer = floor((bmoz+bmhalfh)*cBmGrid/bmmaph);
      [*] = ;               var bmocode : Integer = 0;
      [*] = ;               case TRes(bmpres).itype of
      [*] = ;                  gc_resource_type_gold :
      [*] = ;                  begin
      [*] = ;                     bmocode := 4;
      [*] = ;                     if (bmfree) then bmfg := bmfg + 1;
      [*] = ;                  end;
      [*] = ;                  gc_resource_type_iron :
      [*] = ;                  begin
      [*] = ;                     bmocode := 5;
      [*] = ;                     if (bmfree) then bmfi := bmfi + 1;
      [*] = ;                  end;
      [*] = ;                  gc_resource_type_coal :
      [*] = ;                  begin
      [*] = ;                     bmocode := 6;
      [*] = ;                     if (bmfree) then bmfc := bmfc + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;               if (bmocode>0) then
      [*] = ;               begin
      [*] = ;                  if (not bmfree) then bmocode := 2;
      [*] = ;                  if (bmocx>=0) and (bmocx<cBmGrid) and (bmocy>=0) and (bmocy<cBmGrid) then
      [*] = ;                  if (bmres[bmocx][bmocy]<bmocode) then
      [*] = ;                  bmres[bmocx][bmocy] := bmocode;
      [*] = ;                  if (bmfree) and (bmlisted<8) then
      [*] = ;                  begin
      [*] = ;                     var bmopfx : String = 'o' + IntToStr(bmlisted) + '_';
      [*] = ;                     ParserSetIntValueByKeyByHandle(hmp, bmopfx+'res',  TRes(bmpres).itype);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hmp, bmopfx+'dist', Round(VectorDistance(bmox, 0, bmoz, bmx, 0, bmz)));
      [*] = ;                     ParserSetIntValueByKeyByHandle(hmp, bmopfx+'cx',   bmocx);
      [*] = ;                     ParserSetIntValueByKeyByHandle(hmp, bmopfx+'cy',   bmocy);
      [*] = ;                     bmlisted := bmlisted + 1;
      [*] = ;                  end;
      [*] = ;               end;
      [*] = ;            end;
      [*] = ;         end;
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'ore_free_gold', bmfg);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'ore_free_iron', bmfi);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'ore_free_coal', bmfc);
      [*] = ;         ParserSetIntValueByKeyByHandle(hmp, 'ore_listed',    bmlisted);
      [*] = ;
      [*] = ;         // enemy economy: peasants alive per player - the rush objective is measured here
      [*] = ;         for bmpl := 0 to gc_MaxPlayerCount-1 do
      [*] = ;         if (gPlayer[bmpl].bexists) then
      [*] = ;         begin
      [*] = ;            var bmph : Integer = GetPlayerHandleByIndex(bmpl);
      [*] = ;            var bmocount : Integer = GetPlayerGameObjectsCountByHandle(bmph);
      [*] = ;            var bmpeas : Integer;
      [*] = ;            for bmk := 0 to bmocount-1 do
      [*] = ;            begin
      [*] = ;               var bmgo : Integer = GetGameObjectHandleByIndex(bmk, bmph);
      [*] = ;               var bmpo : Pointer = _unit_GetTObj(bmgo);
      [*] = ;               if (bmpo<>nil) then
      [*] = ;               if (gObjProp[TObj(bmpo).cid][TObj(bmpo).id].usage = gc_obj_usage_peasant) then
      [*] = ;               bmpeas := bmpeas + 1;
      [*] = ;            end;
      [*] = ;            ParserSetIntValueByKeyByHandle(hmp, 'p' + IntToStr(bmpl) + '_peasants', bmpeas);
      [*] = ;         end;
      [*] = ;
      [*] = ;         var bmwmax : Integer = 1;
      [*] = ;         for bmi := 0 to cBmGrid-1 do
      [*] = ;         for bmj := 0 to cBmGrid-1 do
      [*] = ;         if (bmwood[bmi][bmj]>bmwmax) then
      [*] = ;         bmwmax := bmwood[bmi][bmj];
      [*] = ;         for bmj := 0 to cBmGrid-1 do
      [*] = ;         begin
      [*] = ;            bmrow := '';
      [*] = ;            for bmi := 0 to cBmGrid-1 do
      [*] = ;            begin
      [*] = ;               var bmch : String = '.';
      [*] = ;               if (bmwood[bmi][bmj]>0) then
      [*] = ;               begin
      [*] = ;                  if ((bmwood[bmi][bmj]*3)>=bmwmax) then
      [*] = ;                  bmch := '#'
      [*] = ;                  else
      [*] = ;                  bmch := '+';
      [*] = ;               end;
      [*] = ;               case bmres[bmi][bmj] of
      [*] = ;                  1 : bmch := 'S';
      [*] = ;                  2 : bmch := 'x';
      [*] = ;                  4 : bmch := 'G';
      [*] = ;                  5 : bmch := 'I';
      [*] = ;                  6 : bmch := 'C';
      [*] = ;               end;
      [*] = ;               bmrow := bmrow + bmch;
      [*] = ;            end;
      [*] = ;            ParserSetValueByKeyByHandle(hmp, 'rrow'+IntToStr(bmj), bmrow);
      [*] = ;         end;
      [*] = ;         ParserSaveToFileByHandle(hmp, '@@OUT@@coss3_map_P' + IntToStr(plind) + '.dat');
      [*] = ;      end;
      [*] = ;   end;
      [*] = ;
      [*] = ;   ParserSaveToFileByHandle(hbp, '@@OUT@@coss3_eco_P' + IntToStr(plind) + '.dat');
      [*] = ;end;
      [*] = ;// === END BRIDGE STATE ===