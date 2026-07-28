package io.nexus.api.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public UserDetailsService userDetailsService(
        @Value("${ANALYST_USERNAME}") String username,
        @Value("${ANALYST_PASSWORD}") String password,
        PasswordEncoder encoder
    ) {
        var analyst = User.withUsername(username)
            .password(encoder.encode(password))
            .roles("ANALYST")
            .build();
        
        return new InMemoryUserDetailsManager(analyst);
    }

    @Bean
    public SecurityFilterChain securityFilterChain(
        HttpSecurity http
    ) {
        return http
            .csrf(csrf ->
                csrf.ignoringRequestMatchers("/graphql")
            )
            .authorizeHttpRequests(auth ->
                auth
                .requestMatchers(
                    "/graphql",
                    "/graphiql",
                    "/graphiql/**"
                )
                .hasRole("ANALYST")
                .anyRequest()
                .denyAll()
            )
            .httpBasic(Customizer.withDefaults())
            .formLogin(form -> form.disable())
            .sessionManagement(session ->
                session.sessionCreationPolicy(
                    SessionCreationPolicy.STATELESS
                )
            )
            .build();
    }
}
