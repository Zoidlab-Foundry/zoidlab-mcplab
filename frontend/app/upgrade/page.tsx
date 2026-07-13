"use client";
import { useEntitlement } from "../../lib/subscription";
import ProRequiredScreen from "../../components/ProRequiredScreen";

export default function Upgrade() {
  const { ent, state, reload } = useEntitlement();
  return <ProRequiredScreen ent={ent} state={state} reload={reload} packageLabel="Foundry Package 05" />;
}
