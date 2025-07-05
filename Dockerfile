FROM local_discourse/web_only:latest

# 设置目录权限
RUN mkdir -p /shared/state/logrotate && ln -s /shared/state/logrotate /var/lib/logrotate && \
	mkdir -p /shared/state/anacron-spool && ln -s /shared/state/anacron-spool /var/spool/anacron && \
	mkdir -p /shared/uploads && mkdir -p /shared/backups && \
	rm -rf /shared/tmp/{backups,restores} && mkdir -p /shared/tmp/{backups,restores}

# 参考 00-fix-var-logs 文件修改用户权限
RUN rm -f /etc/runit/1.d/00-fix-var-logs && \
    mkdir -p /var/log/nginx && \
    chown -R discourse:discourse /var/log/nginx && \
    chmod -R 644 /var/log/nginx && \
    chmod -R 755 /var/log/nginx && \
    touch /var/log/syslog   && chown -f discourse:discourse /var/log/syslog* && \
    touch /var/log/auth.log && chown -f discourse:discourse /var/log/auth.log* && \
    touch /var/log/kern.log && chown -f discourse:discourse /var/log/kern.log*

# 参考 /etc/service/rsyslog 脚本内容
RUN rm -rf /etc/service/rsyslog
# 容器通过 cron， 使 cron 成为容器的 主进程（PID 1），能直接接收系统信号（如 SIGTERM）；不需要该功能
# seteuid: Operation not permitted
RUN rm -rf /etc/service/cron 

# 参考 /etc/service/unicorn/run, 适配切普通用户的修改
RUN mkdir -p /shared/log/rails && \
    chown -R discourse:discourse /shared/log/rails
COPY ./discourse_config/run /etc/service/unicorn/run
COPY ./discourse_config/00-ensure-links /etc/runit/1.d/00-ensure-links
RUN chmod +x /etc/service/unicorn/run && \
    chmod +x /etc/runit/1.d/00-ensure-links

# 修改 nginx 的启动脚本，适配切换到普通用户的修改
RUN sed -i "s|user www-data;|# user discourse;|g" /etc/nginx/nginx.conf

# 修改 discourse 用户shell的umask配置和历史记录设置
RUN echo "umask 0027" >> /home/discourse/.bashrc && \
    echo "set +o history" >> /home/discourse/.bashrc && \
    sed -i "s|HISTSIZE=1000|HISTSIZE=0|" /home/discourse/.bashrc

# 限制 discourse 用户的密码有效期
RUN chage --maxdays 30 discourse && \
    passwd -| discourse && \
    usermod -s /sbin/nologin sync

WORKDIR /var/www/discourse
COPY ./discourse_config/rails /usr/local/bin/rails

# 修改权限
RUN chown -R discourse:discourse /etc/runit/1.d && \
    chown -R discourse:discourse /etc/service && \
    chmod -R 755 /etc/service && \
    chown -R discourse:discourse /var/www/discourse && \
    chown -R discourse:discourse /shared && \
    chown -R discourse:discourse /var/log && \
    chown -R discourse:discourse /var/lib && \
    chown -R discourse:discourse /var/run && \
    chown -R discourse:discourse /run && \
    chown -R discourse:discourse /tmp && \
    chown -R discourse:discourse /dev && \
    chown -R discourse:discourse /var/spool && \
    chown -R discourse:discourse /etc/ssl

RUN apt purge postgresql-client-15 -y && \
    apt purge postgresql-client-common -y && \
    apt autoremove -y && \
    apt update && \
    apt install postgresql-client-16 -y && \
    pg_dump --version

# 切换到非root用户
USER discourse

RUN . /home/discourse/.bashrc

# 保留原有的ENTRYPOINT和CMD
# ENTRYPOINT ["sh", "-c", "rails db:migrate && /sbin/boot"]
