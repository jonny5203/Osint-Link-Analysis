package io.nexus.api.investigation;

import org.springframework.stereotype.Controller;
import org.springframework.transaction.annotation.Transactional;

/** Investigation mutation resolvers (PLAN.md T8.3). Each resolver is @Transactional. */
@Controller
@Transactional
public class InvestigationController {
    // TODO(T8.3): @MutationMapping createInvestigation / addEntity / annotate / saveLayout
}
