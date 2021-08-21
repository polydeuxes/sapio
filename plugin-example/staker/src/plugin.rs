// Copyright Judica, Inc 2021
//
// This Source Code Form is subject to the terms of the Mozilla Public
//  License, v. 2.0. If a copy of the MPL was not distributed with this
//  file, You can obtain one at https://mozilla.org/MPL/2.0/.

use batching_trait::{BatchingTraitVersion0_1_1, Payment};
#[deny(missing_docs)]
use sapio::contract::*;
use sapio::util::amountrange::*;
use sapio::*;
use sapio_base::timelocks::{AnyRelTimeLock, RelHeight};
use sapio_wasm_plugin::client::*;
use sapio_wasm_plugin::*;
use schemars::*;
use serde::*;
use std::collections::VecDeque;
use std::convert::{TryInto, TryFrom};
use sapio_contrib::contracts::staked_signer::{Staker, Operational};
/// # Bonded Staker
type BondedStaker = Staker<Operational>;
#[derive(JsonSchema, Deserialize)]
#[serde(transparent)]
struct Wrapper(BondedStaker);

impl From<Wrapper> for BondedStaker {
    fn from(v: Wrapper) -> Self {
        v.0
    }
}
REGISTER![[BondedStaker, Wrapper], "logo.png"];
