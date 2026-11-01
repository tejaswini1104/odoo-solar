-- Approved repairs that need a replacement now wait for the warehouse to dispatch it.
UPDATE service_tickets SET status = 'Awaiting Dispatch' WHERE status = 'In Progress' AND needs_replacement = TRUE;
