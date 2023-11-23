import numpy as np
from numba import njit, typed, types

from quantfreedom.enums import *
from quantfreedom.helper_funcs import dos_cart_product
from quantfreedom.nb_funcs.nb_custom_logger import *

from quantfreedom.nb_funcs.nb_order_handler.nb_decrease_position import nb_decrease_position
from quantfreedom.nb_funcs.nb_order_handler.nb_increase_position import (
    AccExOther,
    OrderInfo,
    nb_long_min_amount,
    nb_long_rpa_slbcb,
)
from quantfreedom.nb_funcs.nb_order_handler.nb_take_profit import nb_long_c_tp_hit_regular, nb_long_tp_rr
from quantfreedom.nb_funcs.nb_order_handler.nb_leverage import (
    nb_long_check_liq_hit,
    nb_long_dynamic_lev,
    nb_long_static_lev,
)
from quantfreedom.nb_funcs.nb_helper_funcs import (
    get_data_for_plotting,
    nb_fill_order_records,
    nb_float_to_str,
    nb_get_dos,
    nb_max_price_getter,
    nb_min_price_getter,
    nb_sl_to_entry,
    nb_sl_to_z_e_pass,
    nb_long_sl_to_zero,
    order_records_to_df,
)
from quantfreedom.nb_funcs.nb_order_handler.nb_stop_loss import (
    nb_long_c_sl_hit,
    nb_long_cm_sl_to_be,
    nb_long_cm_sl_to_be_pass,
    nb_long_cm_tsl,
    nb_long_cm_tsl_pass,
    nb_long_sl_bcb,
    nb_move_stop_loss,
    nb_move_stop_loss_pass,
)
from quantfreedom.plotting.plotting_base import plot_or_results


def nb_sim_get_or(
    backtest_settings: BacktestSettings,
    candles: np.array,
    dos_arrays: DynamicOrderSettingsArrays,
    dos_index: int,
    evaluate,
    exchange_settings: ExchangeSettings,
    get_current_ind_settings,
    get_ind_set_str,
    get_total_ind_settings,
    ind_creator,
    ind_set_index: int,
    nb_logger_type: NBLoggerType,
    starting_equity: float,
    static_os: StaticOrderSettings,
    plot_results: bool = False,
):
    dos_cart_arrays = dos_cart_product(
        dos_arrays=dos_arrays,
    )

    """
    #########################################
    #########################################
    #########################################
                    Logger
                    Logger
                    Logger
    #########################################
    #########################################
    #########################################
    """
    log_func_type = types.void(types.unicode_type)
    log_func_list = typed.List.empty_list(log_func_type.as_type())

    str_func_type = types.unicode_type(types.float64)
    str_func_list = typed.List.empty_list(str_func_type.as_type())

    if nb_logger_type == NBLoggerType.Print:
        log_func_list.append(nb_log_debug)
        log_func_list.append(nb_log_info)
        log_func_list.append(nb_log_warning)
        log_func_list.append(nb_log_error)

        str_func_list.append(nb_float_to_str)
        str_func_list.append(nb_log_datetime)
        str_func_list.append(nb_candle_body_str)
        str_func_list.append(nb_z_or_e_str)
        str_func_list.append(nb_os_to_str)

    elif nb_logger_type == NBLoggerType.Pass:
        log_func_list.append(nb_logger_pass)
        log_func_list.append(nb_logger_pass)
        log_func_list.append(nb_logger_pass)
        log_func_list.append(nb_logger_pass)

        str_func_list.append(nb_stringer_pass)
        str_func_list.append(nb_stringer_pass)
        str_func_list.append(nb_stringer_pass)
        str_func_list.append(nb_stringer_pass)
        str_func_list.append(nb_stringer_pass)

    else:
        raise Exception("You need to select the correct logger type")
    """
    #########################################
    #########################################
    #########################################
                    Trading
                    Trading
                    Trading
    #########################################
    #########################################
    #########################################
    """
    if static_os.long_or_short == LongOrShortType.Long:
        # Decrease Position
        dec_pos_calculator = nb_decrease_position

        """
        #########################################
        #########################################
        #########################################
                        Stop Loss
                        Stop Loss
                        Stop Loss
        #########################################
        #########################################
        #########################################
        """

        # stop loss calulator
        if static_os.sl_strategy_type == StopLossStrategyType.SLBasedOnCandleBody:
            sl_calculator = nb_long_sl_bcb
            checker_sl_hit = nb_long_c_sl_hit
            if static_os.pg_min_max_sl_bcb == PriceGetterType.Min:
                sl_bcb_price_getter = nb_min_price_getter
            elif static_os.pg_min_max_sl_bcb == PriceGetterType.Max:
                sl_bcb_price_getter = nb_max_price_getter

        # SL break even
        if static_os.sl_to_be_bool:
            checker_sl_to_be = nb_long_cm_sl_to_be
            # setting up stop loss be zero or entry
            if static_os.z_or_e_type == ZeroOrEntryType.ZeroLoss:
                zero_or_entry_calc = nb_long_sl_to_zero
            elif static_os.z_or_e_type == ZeroOrEntryType.AverageEntry:
                zero_or_entry_calc = nb_sl_to_entry
        else:
            checker_sl_to_be = nb_long_cm_sl_to_be_pass
            zero_or_entry_calc = nb_sl_to_z_e_pass

        # Trailing stop loss
        if static_os.trail_sl_bool:
            checker_tsl = nb_long_cm_tsl
        else:
            checker_tsl = nb_long_cm_tsl_pass

        if static_os.trail_sl_bool or static_os.sl_to_be_bool:
            sl_mover = nb_move_stop_loss
        else:
            sl_mover = nb_move_stop_loss_pass

        """
        #########################################
        #########################################
        #########################################
                    Increase position
                    Increase position
                    Increase position
        #########################################
        #########################################
        #########################################
        """

        if static_os.sl_strategy_type == StopLossStrategyType.SLBasedOnCandleBody:
            if static_os.increase_position_type == IncreasePositionType.RiskPctAccountEntrySize:
                inc_pos_calculator = nb_long_rpa_slbcb

            elif static_os.increase_position_type == IncreasePositionType.SmalletEntrySizeAsset:
                inc_pos_calculator = nb_long_min_amount

        """
        #########################################
        #########################################
        #########################################
                        Leverage
                        Leverage
                        Leverage
        #########################################
        #########################################
        #########################################
        """

        if static_os.leverage_strategy_type == LeverageStrategyType.Dynamic:
            lev_calculator = nb_long_dynamic_lev
        else:
            lev_calculator = nb_long_static_lev

        checker_liq_hit = nb_long_check_liq_hit
        """
        #########################################
        #########################################
        #########################################
                        Take Profit
                        Take Profit
                        Take Profit
        #########################################
        #########################################
        #########################################
        """

        if static_os.tp_strategy_type == TakeProfitStrategyType.RiskReward:
            tp_calculator = nb_long_tp_rr
            checker_tp_hit = nb_long_c_tp_hit_regular
        elif static_os.tp_strategy_type == TakeProfitStrategyType.Provided:
            pass
    """
    #########################################
    #########################################
    #########################################
                Other Settings
                Other Settings
                Other Settings
    #########################################
    #########################################
    #########################################
    """

    if static_os.tp_fee_type == TakeProfitFeeType.Market:
        exit_fee_pct = exchange_settings.market_fee_pct
    else:
        exit_fee_pct = exchange_settings.limit_fee_pct
    """
    #########################################
    #########################################
    #########################################
                End User Setup
                End User Setup
                End User Setup
    #########################################
    #########################################
    #########################################
    """

    order_records = nb_run_sim_or(
        backtest_settings=backtest_settings,
        candles=candles,
        checker_liq_hit=checker_liq_hit,
        checker_sl_hit=checker_sl_hit,
        checker_sl_to_be=checker_sl_to_be,
        checker_tp_hit=checker_tp_hit,
        checker_tsl=checker_tsl,
        dec_pos_calculator=dec_pos_calculator,
        dos_cart_arrays=dos_cart_arrays,
        evaluate=evaluate,
        exchange_settings=exchange_settings,
        exit_fee_pct=exit_fee_pct,
        get_current_ind_settings=get_current_ind_settings,
        get_ind_set_str=get_ind_set_str,
        inc_pos_calculator=inc_pos_calculator,
        ind_creator=ind_creator,
        lev_calculator=lev_calculator,
        logger=log_func_list,
        sl_bcb_price_getter=sl_bcb_price_getter,
        sl_calculator=sl_calculator,
        sl_mover=sl_mover,
        starting_equity=starting_equity,
        stringer=str_func_list,
        dos_index=dos_index,
        ind_set_index=ind_set_index,
        tp_calculator=tp_calculator,
        zero_or_entry_calc=zero_or_entry_calc,
    )
    order_records_df = order_records_to_df(order_records)
    data = get_data_for_plotting(order_records_df, candles)
    if plot_results:
        plot_or_results(candles=candles, order_records_df=order_records_df)
    return order_records_df, data


@njit(cache=True)
def nb_run_sim_or(
    backtest_settings: BacktestSettings,
    candles: np.array,
    checker_liq_hit,
    checker_sl_hit,
    dos_index: int,
    checker_sl_to_be,
    ind_set_index: int,
    checker_tp_hit,
    checker_tsl,
    dec_pos_calculator,
    dos_cart_arrays: DynamicOrderSettingsArrays,
    evaluate,
    exchange_settings: ExchangeSettings,
    exit_fee_pct: float,
    get_current_ind_settings,
    get_ind_set_str,
    inc_pos_calculator,
    ind_creator,
    lev_calculator,
    logger,
    sl_bcb_price_getter,
    sl_calculator,
    sl_mover,
    starting_equity: float,
    stringer,
    tp_calculator,
    zero_or_entry_calc,
):
    market_fee_pct = exchange_settings.market_fee_pct
    leverage_tick_step = exchange_settings.leverage_tick_step
    price_tick_step = exchange_settings.price_tick_step
    asset_tick_step = exchange_settings.asset_tick_step
    min_asset_size = exchange_settings.min_asset_size
    max_asset_size = exchange_settings.max_asset_size
    max_leverage = exchange_settings.max_leverage
    min_leverage = exchange_settings.min_leverage
    mmr_pct = exchange_settings.mmr_pct

    indicator_settings = get_current_ind_settings(
        ind_set_index=ind_set_index,
        logger=logger,
    )

    logger("nb_sim_ordder_records.py - nb_run_backtest() - Indicator settings index=" + str(ind_set_index))

    logger(get_ind_set_str(indicator_settings=indicator_settings, stringer=stringer))

    dynamic_order_settings = nb_get_dos(
        dos_cart_arrays=dos_cart_arrays,
        dos_index=dos_index,
    )
    logger("nb_sim_ordder_records.py - nb_run_backtest() - Dynamic Order settings index=" + str(dos_index))
    logger(
        "nb_sim_ordder_records.py - nb_run_backtest() - Created Dynamic Order Settings"
        + "\nmax_equity_risk_pct= "
        + stringer[StringerFuncType.float_to_str](round(dynamic_order_settings.max_equity_risk_pct * 100, 3))
        + "\nmax_trades= "
        + str(dynamic_order_settings.max_trades)
        + "\nrisk_account_pct_size= "
        + stringer[StringerFuncType.float_to_str](round(dynamic_order_settings.risk_account_pct_size * 100, 3))
        + "\nrisk_reward= "
        + stringer[StringerFuncType.float_to_str](dynamic_order_settings.risk_reward)
        + "\nsl_based_on_add_pct= "
        + stringer[StringerFuncType.float_to_str](round(dynamic_order_settings.sl_based_on_add_pct * 100, 3))
        + "\nsl_based_on_lookback= "
        + str(dynamic_order_settings.sl_based_on_lookback)
        + "\nsl_bcb_type= "
        + stringer[StringerFuncType.candle_body_str](dynamic_order_settings.sl_bcb_type)
        + "\nsl_to_be_cb_type= "
        + stringer[StringerFuncType.candle_body_str](dynamic_order_settings.sl_to_be_cb_type)
        + "\nsl_to_be_when_pct= "
        + stringer[StringerFuncType.float_to_str](round(dynamic_order_settings.sl_to_be_when_pct * 100, 3))
        + "\nstatic_leverage= "
        + stringer[StringerFuncType.float_to_str](dynamic_order_settings.static_leverage)
        + "\ntrail_sl_bcb_type= "
        + stringer[StringerFuncType.candle_body_str](dynamic_order_settings.trail_sl_bcb_type)
        + "\ntrail_sl_by_pct= "
        + stringer[StringerFuncType.float_to_str](round(dynamic_order_settings.trail_sl_by_pct * 100, 3))
        + "\ntrail_sl_when_pct= "
        + stringer[StringerFuncType.float_to_str](round(dynamic_order_settings.trail_sl_when_pct * 100, 3))
    )

    logger("nb_sim_ordder_records.py - nb_run_backtest() - Starting Bar=" + str(starting_bar))

    account_state: AccountState = AccountState(
        # where we are at
        ind_set_index=-1,
        dos_index=-1,
        bar_index=-1,
        timestamp=-1,
        # account info
        available_balance=starting_equity,
        cash_borrowed=0.0,
        cash_used=0.0,
        equity=starting_equity,
        fees_paid=0.0,
        possible_loss=0,
        realized_pnl=0.0,
        total_trades=0,
    )
    order_result: OrderResult = OrderResult(
        average_entry=0.0,
        can_move_sl_to_be=False,
        entry_price=0.0,
        entry_size_asset=0.0,
        entry_size_usd=0.0,
        exit_price=0.0,
        leverage=1.0,
        liq_price=0.0,
        order_status=OrderStatus.Nothing,
        position_size_asset=0.0,
        position_size_usd=0.0,
        sl_pct=0.0,
        sl_price=0.0,
        tp_pct=0.0,
        tp_price=0.0,
    )

    logger("nb_sim_ordder_records.py - nb_run_backtest() - account state order results pnl array all set to default")
    total_bars = candles.shape[0]
    order_records = np.empty(total_bars, dtype=or_dt)
    or_index = 0
    for bar_index in range(starting_bar, total_bars):
        logger("\n\n")
        logger(
            (
                "nb_sim_ordder_records.py - nb_run_backtest() - ind_idx="
                + str(ind_set_index)
                + " dos_idx="
                + str(dos_index)
                + " bar_idx="
                + str(bar_index)
                + " timestamp= "
                + stringer[StringerFuncType.log_datetime](candles[bar_index, CandleBodyType.Timestamp])
            )
        )

        if order_result.position_size_usd > 0:
            try:
                # checking if sl hit
                logger("nb_sim_ordder_records.py - nb_run_backtest() - check_stop_loss_hit")
                sl_hit_bool = checker_sl_hit(
                    current_candle=candles[bar_index, :],
                    sl_price=order_result.sl_price,
                    logger=logger,
                    stringer=stringer,
                )
                if sl_hit_bool:
                    logger("nb_sim_ordder_records.py - nb_run_backtest() - decrease_position")
                    (
                        account_state,
                        order_result,
                    ) = dec_pos_calculator(
                        average_entry=order_result.average_entry,
                        bar_index=bar_index,
                        dos_index=dos_index,
                        equity=account_state.equity,
                        exit_fee_pct=market_fee_pct,
                        exit_price=order_result.sl_price,
                        ind_set_index=ind_set_index,
                        logger=logger,
                        market_fee_pct=market_fee_pct,
                        order_status=OrderStatus.StopLossFilled,
                        position_size_asset=order_result.position_size_asset,
                        stringer=stringer,
                        timestamp=int(candles[bar_index, CandleBodyType.Timestamp]),
                    )
                    or_index = nb_fill_order_records(
                        account_state=account_state,
                        or_index=or_index,
                        order_result=order_result,
                        order_records=order_records[or_index],
                    )
                    raise DecreasePosition

                # checking if liq hit
                logger("nb_sim_ordder_records.py - nb_run_backtest() - check_liq_hit")
                liq_hit_bool = checker_liq_hit(
                    current_candle=candles[bar_index, :],
                    liq_price=order_result.liq_price,
                    logger=logger,
                    stringer=stringer,
                )
                if liq_hit_bool:
                    logger("nb_sim_ordder_records.py - nb_run_backtest() - decrease_position")
                    (
                        account_state,
                        order_result,
                    ) = dec_pos_calculator(
                        average_entry=order_result.average_entry,
                        bar_index=bar_index,
                        dos_index=dos_index,
                        equity=account_state.equity,
                        exit_fee_pct=market_fee_pct,
                        exit_price=order_result.liq_price,
                        ind_set_index=ind_set_index,
                        logger=logger,
                        market_fee_pct=market_fee_pct,
                        order_status=OrderStatus.LiquidationFilled,
                        position_size_asset=order_result.position_size_asset,
                        stringer=stringer,
                        timestamp=int(candles[bar_index, CandleBodyType.Timestamp]),
                    )
                    or_index = nb_fill_order_records(
                        account_state=account_state,
                        or_index=or_index,
                        order_result=order_result,
                        order_records=order_records[or_index],
                    )
                    raise DecreasePosition

                # checking if tp hit
                logger("nb_sim_ordder_records.py - nb_run_backtest() - check_tp_hit")
                tp_hit_bool = checker_tp_hit(
                    current_candle=candles[bar_index, :],
                    tp_price=order_result.tp_price,
                    logger=logger,
                    stringer=stringer,
                )
                if tp_hit_bool:
                    logger("nb_sim_ordder_records.py - nb_run_backtest() - decrease_position")
                    (
                        account_state,
                        order_result,
                    ) = dec_pos_calculator(
                        average_entry=order_result.average_entry,
                        bar_index=bar_index,
                        dos_index=dos_index,
                        equity=account_state.equity,
                        exit_fee_pct=exit_fee_pct,
                        exit_price=order_result.tp_price,
                        ind_set_index=ind_set_index,
                        logger=logger,
                        market_fee_pct=market_fee_pct,
                        order_status=OrderStatus.TakeProfitFilled,
                        position_size_asset=order_result.position_size_asset,
                        stringer=stringer,
                        timestamp=int(candles[bar_index, CandleBodyType.Timestamp]),
                    )
                    or_index = nb_fill_order_records(
                        account_state=account_state,
                        or_index=or_index,
                        order_result=order_result,
                        order_records=order_records[or_index],
                    )
                    raise DecreasePosition

                # checking to move stop loss

                logger("nb_sim_ordder_records.py - nb_run_backtest() - check_move_stop_loss_to_be")
                temp_sl = checker_sl_to_be(
                    average_entry=order_result.average_entry,
                    can_move_sl_to_be=order_result.can_move_sl_to_be,
                    candle_body_type=dynamic_order_settings.sl_to_be_cb_type,
                    current_candle=candles[bar_index, :],
                    logger=logger,
                    market_fee_pct=market_fee_pct,
                    price_tick_step=price_tick_step,
                    sl_price=order_result.sl_price,
                    sl_to_be_when_pct=dynamic_order_settings.sl_to_be_when_pct,
                    stringer=stringer,
                    zero_or_entry_calc=zero_or_entry_calc,
                )
                if temp_sl > 0:
                    logger("nb_sim_ordder_records.py - nb_run_backtest() - move_stop_loss")
                    account_state, order_result = sl_mover(
                        account_state=account_state,
                        bar_index=bar_index,
                        can_move_sl_to_be=False,
                        dos_index=dos_index,
                        stringer=stringer,
                        ind_set_index=ind_set_index,
                        logger=logger,
                        order_result=order_result,
                        order_status=OrderStatus.MovedSLToBE,
                        sl_price=temp_sl,
                        timestamp=int(candles[bar_index, CandleBodyType.Timestamp]),
                    )
                    or_index = nb_fill_order_records(
                        account_state=account_state,
                        or_index=or_index,
                        order_result=order_result,
                        order_records=order_records[or_index],
                    )
                    raise MoveStopLoss
                # Checking to move trailing stop loss

                logger("nb_sim_ordder_records.py - nb_run_backtest() - check_move_trailing_stop_loss")
                temp_tsl = checker_tsl(
                    average_entry=order_result.average_entry,
                    candle_body_type=dynamic_order_settings.trail_sl_bcb_type,
                    current_candle=candles[bar_index, :],
                    logger=logger,
                    price_tick_step=price_tick_step,
                    sl_price=order_result.sl_price,
                    stringer=stringer,
                    trail_sl_by_pct=dynamic_order_settings.trail_sl_by_pct,
                    trail_sl_when_pct=dynamic_order_settings.trail_sl_when_pct,
                )
                if temp_tsl > 0:
                    logger("nb_sim_ordder_records.py - nb_run_backtest() - move_stop_loss")
                    account_state, order_result = sl_mover(
                        account_state=account_state,
                        bar_index=bar_index,
                        can_move_sl_to_be=False,
                        dos_index=dos_index,
                        ind_set_index=ind_set_index,
                        logger=logger,
                        order_result=order_result,
                        order_status=OrderStatus.MovedTSL,
                        sl_price=temp_tsl,
                        stringer=stringer,
                        timestamp=int(candles[bar_index, CandleBodyType.Timestamp]),
                    )
                    or_index = nb_fill_order_records(
                        account_state=account_state,
                        or_index=or_index,
                        order_result=order_result,
                        order_records=order_records[or_index],
                    )
                    raise MoveStopLoss

            # except Exception as e:
            #     logger(f"nb_sim_ordder_records.py - nb_run_backtest() - Checking hit Exception -> {e}")
            #     pass
            except Exception:
                logger("nb_sim_ordder_records.py - nb_run_backtest() - Checking hit Exception")
                pass
        else:
            logger("nb_sim_ordder_records.py - nb_run_backtest() - Not in a pos so not checking SL Liq or TP")
        logger("nb_sim_ordder_records.py - nb_run_backtest() - strategy evaluate")
        eval_bool = evaluate(
            bar_index=bar_index,
            starting_bar=starting_bar,
            candles=candles,
            indicator_settings=indicator_settings,
            ind_creator=ind_creator,
            logger=logger,
            stringer=stringer,
        )
        if eval_bool:
            try:
                logger("nb_sim_ordder_records.py - nb_run_backtest() - calculate_stop_loss")
                sl_price = sl_calculator(
                    bar_index=bar_index,
                    candles=candles,
                    logger=logger,
                    stringer=stringer,
                    price_tick_step=price_tick_step,
                    sl_based_on_add_pct=dynamic_order_settings.sl_based_on_add_pct,
                    sl_based_on_lookback=dynamic_order_settings.sl_based_on_lookback,
                    sl_bcb_price_getter=sl_bcb_price_getter,
                    sl_bcb_type=dynamic_order_settings.sl_bcb_type,
                )

                logger("nb_sim_ordder_records.py - nb_run_backtest() - calculate_increase_posotion")
                (
                    average_entry,
                    entry_price,
                    entry_size_asset,
                    entry_size_usd,
                    position_size_asset,
                    position_size_usd,
                    possible_loss,
                    total_trades,
                    sl_pct,
                ) = inc_pos_calculator(
                    acc_ex_other=AccExOther(
                        account_state_equity=account_state.equity,
                        asset_tick_step=asset_tick_step,
                        market_fee_pct=market_fee_pct,
                        max_asset_size=max_asset_size,
                        min_asset_size=min_asset_size,
                        possible_loss=account_state.possible_loss,
                        price_tick_step=price_tick_step,
                        total_trades=account_state.total_trades,
                    ),
                    order_info=OrderInfo(
                        average_entry=order_result.average_entry,
                        entry_price=candles[bar_index, CandleBodyType.Close],
                        in_position=order_result.position_size_usd > 0,
                        max_equity_risk_pct=dynamic_order_settings.max_equity_risk_pct,
                        max_trades=dynamic_order_settings.max_trades,
                        position_size_asset=order_result.position_size_asset,
                        position_size_usd=order_result.position_size_usd,
                        risk_account_pct_size=dynamic_order_settings.risk_account_pct_size,
                        sl_price=sl_price,
                    ),
                    logger=logger,
                    stringer=stringer,
                )

                logger("nb_sim_ordder_records.py - nb_run_backtest() - calculate_leverage")
                (
                    available_balance,
                    cash_borrowed,
                    cash_used,
                    leverage,
                    liq_price,
                ) = lev_calculator(
                    available_balance=account_state.available_balance,
                    average_entry=average_entry,
                    cash_borrowed=account_state.cash_borrowed,
                    cash_used=account_state.cash_used,
                    entry_size_usd=entry_size_usd,
                    max_leverage=max_leverage,
                    min_leverage=min_leverage,
                    stringer=stringer,
                    mmr_pct=mmr_pct,
                    sl_price=sl_price,
                    static_leverage=dynamic_order_settings.static_leverage,
                    leverage_tick_step=leverage_tick_step,
                    price_tick_step=price_tick_step,
                    logger=logger,
                )

                logger("nb_sim_ordder_records.py - nb_run_backtest() - calculate_take_profit")
                (
                    can_move_sl_to_be,
                    tp_price,
                    tp_pct,
                ) = tp_calculator(
                    average_entry=average_entry,
                    market_fee_pct=market_fee_pct,
                    position_size_usd=position_size_usd,
                    possible_loss=possible_loss,
                    price_tick_step=price_tick_step,
                    risk_reward=dynamic_order_settings.risk_reward,
                    tp_fee_pct=exit_fee_pct,
                    stringer=stringer,
                    logger=logger,
                )

                logger("nb_sim_ordder_records.py - nb_run_backtest() - Recorded Trade")
                account_state = AccountState(
                    # where we are at
                    ind_set_index=ind_set_index,
                    dos_index=dos_index,
                    bar_index=bar_index + 1,  # put plus 1 because we need to place entry on next bar
                    timestamp=int(candles[bar_index + 1, CandleBodyType.Timestamp]),
                    # account info
                    available_balance=available_balance,
                    cash_borrowed=cash_borrowed,
                    cash_used=cash_used,
                    equity=account_state.equity,
                    fees_paid=0.0,
                    possible_loss=possible_loss,
                    realized_pnl=0.0,
                    total_trades=total_trades,
                )
                order_result = OrderResult(
                    average_entry=average_entry,
                    can_move_sl_to_be=can_move_sl_to_be,
                    entry_price=entry_price,
                    entry_size_asset=entry_size_asset,
                    entry_size_usd=entry_size_usd,
                    exit_price=0.0,
                    leverage=leverage,
                    liq_price=liq_price,
                    order_status=OrderStatus.EntryFilled,
                    position_size_asset=position_size_asset,
                    position_size_usd=position_size_usd,
                    sl_pct=sl_pct,
                    sl_price=sl_price,
                    tp_pct=tp_pct,
                    tp_price=tp_price,
                )
                or_index = nb_fill_order_records(
                    account_state=account_state,
                    or_index=or_index,
                    order_result=order_result,
                    order_records=order_records[or_index],
                )
                logger("nb_sim_ordder_records.py - nb_run_backtest() - Account State OrderResult")
            # except Exception as e:
            #     logger(f"nb_sim_ordder_records.py - nb_run_backtest() - Exception hit in eval strat -> {e}")
            #     pass
            except Exception:
                logger("nb_sim_ordder_records.py - nb_run_backtest() - Exception hit in eval strat")
                pass
    return order_records[:or_index]